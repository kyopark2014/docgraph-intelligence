#!/usr/bin/env python3
"""
AWS Infrastructure Installer for DocGraph Intelligence (local app).

Reuses shared RAG-project resources when they already exist (same as agent-skills):
  - S3: storage-for-rag-project-{account}-{region}
  - CloudFront: comment "CloudFront-for-rag-project" (S3 origin)

Also creates/reuses shared Secrets Manager secret `tavilyapikey` (same as agent-skills).
"""

import argparse
import json
import logging
import time
from typing import Dict

import boto3
from botocore.exceptions import ClientError

# Configuration
project_name = "docgraph"  # at least 3 characters
region = "us-west-2"

# Shared with agent-skills / other RAG projects — do not invent a new bucket/CF
cloudfront_comment = "CloudFront-for-rag-project"
oai_comment = "OAI for rag-project"

sts_client = boto3.client("sts", region_name=region)
account_id = sts_client.get_caller_identity()["Account"]

s3_client = boto3.client("s3", region_name=region)
secrets_client = boto3.client("secretsmanager", region_name=region)
cloudfront_client = boto3.client("cloudfront", region_name=region)

bucket_name = f"storage-for-rag-project-{account_id}-{region}"


def setup_logging(log_level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def _ensure_bucket_folders(bucket: str) -> None:
    docs_prefix = f"docs/{project_name}/"
    for folder in [docs_prefix, "artifacts/"]:
        try:
            s3_client.put_object(Bucket=bucket, Key=folder, Body=b"")
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucket":
                logger.warning(f"Failed to create {folder} folder: {e}")


def create_s3_bucket() -> str:
    """Create shared S3 bucket, or reuse if it already exists."""
    logger.info(f"[1/3] Creating/reusing S3 bucket: {bucket_name}")

    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.warning(f"S3 bucket already exists (reusing): {bucket_name}")
        _ensure_bucket_folders(bucket_name)
        return bucket_name
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        # 404 / NoSuchBucket / 403 — try create; 403 may mean exists but no Head permission
        if error_code not in ("404", "NoSuchBucket", "403"):
            logger.error(f"Failed to check S3 bucket: {e}")
            raise

    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )

        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "POST", "PUT"],
                        "AllowedOrigins": ["*"],
                    }
                ]
            },
        )

        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Suspended"},
        )

        _ensure_bucket_folders(bucket_name)
        logger.info(f"✓ S3 bucket created successfully: {bucket_name}")
        return bucket_name

    except ClientError as e:
        if e.response["Error"]["Code"] in ["BucketAlreadyExists", "BucketAlreadyOwnedByYou"]:
            logger.warning(f"S3 bucket already exists (reusing): {bucket_name}")
            _ensure_bucket_folders(bucket_name)
            return bucket_name
        logger.error(f"Failed to create S3 bucket: {e}")
        raise


def create_cloudfront_distribution(s3_bucket_name: str) -> Dict[str, str]:
    """Create CloudFront (S3 origin), or reuse shared rag-project distribution."""
    logger.info("[2/3] Creating/reusing CloudFront distribution")

    try:
        distributions = cloudfront_client.list_distributions()
        for dist in distributions.get("DistributionList", {}).get("Items", []):
            if cloudfront_comment not in dist.get("Comment", ""):
                continue
            if dist.get("Enabled", False):
                logger.warning(
                    f"CloudFront distribution already exists (reusing): {dist['DomainName']}"
                )
                return {"id": dist["Id"], "domain": dist["DomainName"]}
            logger.warning(
                f"CloudFront distribution exists but is disabled: {dist['DomainName']}"
            )
            dist_config_response = cloudfront_client.get_distribution_config(Id=dist["Id"])
            dist_config = dist_config_response["DistributionConfig"]
            dist_config["Enabled"] = True
            cloudfront_client.update_distribution(
                Id=dist["Id"],
                DistributionConfig=dist_config,
                IfMatch=dist_config_response["ETag"],
            )
            return {"id": dist["Id"], "domain": dist["DomainName"]}
    except Exception as e:
        logger.debug(f"Error checking existing CloudFront distributions: {e}")

    oai_id = None
    try:
        oai_list = cloudfront_client.list_cloud_front_origin_access_identities()
        for oai in oai_list.get("CloudFrontOriginAccessIdentityList", {}).get("Items", []):
            if oai_comment in oai.get("Comment", "") or "rag-project" in oai.get("Comment", ""):
                oai_id = oai["Id"]
                logger.info(f"  Using existing Origin Access Identity: {oai_id}")
                break
        if not oai_id:
            oai_response = cloudfront_client.create_cloud_front_origin_access_identity(
                CloudFrontOriginAccessIdentityConfig={
                    "CallerReference": f"rag-project-s3-oai-{int(time.time())}",
                    "Comment": oai_comment,
                }
            )
            oai_id = oai_response["CloudFrontOriginAccessIdentity"]["Id"]
            logger.info(f"  Created Origin Access Identity: {oai_id}")
    except ClientError as e:
        logger.error(f"Failed to handle Origin Access Identity: {e}")
        raise

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontAccess",
                "Effect": "Allow",
                "Principal": {
                    "AWS": (
                        f"arn:aws:iam::cloudfront:user/"
                        f"CloudFront Origin Access Identity {oai_id}"
                    )
                },
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{s3_bucket_name}/*",
            }
        ],
    }
    try:
        time.sleep(5)
        s3_client.put_bucket_policy(Bucket=s3_bucket_name, Policy=json.dumps(bucket_policy))
        logger.info("  Updated S3 bucket policy for CloudFront access")
    except ClientError as e:
        logger.error(f"Failed to update S3 bucket policy: {e}")
        raise

    origin_id = "s3-rag-project"
    distribution_config = {
        "CallerReference": f"rag-project-{int(time.time())}",
        "Comment": cloudfront_comment,
        "DefaultRootObject": "index.html",
        "DefaultCacheBehavior": {
            "TargetOriginId": origin_id,
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"],
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
            },
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
            "Compress": True,
        },
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": origin_id,
                    "DomainName": f"{s3_bucket_name}.s3.{region}.amazonaws.com",
                    "S3OriginConfig": {
                        "OriginAccessIdentity": f"origin-access-identity/cloudfront/{oai_id}"
                    },
                }
            ],
        },
        "Enabled": True,
        "PriceClass": "PriceClass_200",
    }

    response = cloudfront_client.create_distribution(DistributionConfig=distribution_config)
    distribution_id = response["Distribution"]["Id"]
    distribution_domain = response["Distribution"]["DomainName"]
    logger.info(f"✓ CloudFront distribution created: {distribution_domain}")
    logger.info(f"  S3 origin: {s3_bucket_name}")
    return {"id": distribution_id, "domain": distribution_domain}


def create_secrets(skip_prompt: bool = False) -> Dict[str, str]:
    """Create shared Tavily secret, or reuse if it already exists (agent-skills)."""
    logger.info("[3/3] Creating/reusing Secrets Manager secrets")

    # Shared name — same as agent-skills / application/utils.py
    secret_name = "tavilyapikey"
    secret_value = {
        "project_name": project_name,
        "tavily_api_key": "",
        "nova_act_api_key": "",
    }

    try:
        response = secrets_client.describe_secret(SecretId=secret_name)
        logger.warning(f"  Secret already exists (reusing): {secret_name}")
        return {"tavily": response["ARN"]}
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            logger.error(f"  Failed to check secret {secret_name}: {e}")
            raise

    if not skip_prompt:
        logger.info("Enter API keys when prompted (press Enter to skip and leave empty):")
        api_key = input(f"Creating {secret_name} - Tavily API Key: ").strip()
        secret_value["tavily_api_key"] = api_key
        secret_value["nova_act_api_key"] = api_key

    try:
        response = secrets_client.create_secret(
            Name=secret_name,
            Description="secret for tavily api key",
            SecretString=json.dumps(secret_value),
        )
        logger.info(f"  ✓ Created secret: {secret_name}")
        return {"tavily": response["ARN"]}
    except ClientError as create_error:
        logger.error(f"  Failed to create secret {secret_name}: {create_error}")
        raise


def update_config(s3_bucket_name: str, cloudfront_domain: str) -> None:
    """Write project/S3/CloudFront fields into application/config.json."""
    config_path = "application/config.json"
    config_data: Dict = {}

    try:
        with open(config_path, "r") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        logger.info(f"Creating new {config_path}")
    except Exception as e:
        logger.warning(f"Could not read existing {config_path}: {e}")

    config_data.update(
        {
            "projectName": project_name,
            "accountId": account_id,
            "region": region,
            "s3_bucket": s3_bucket_name,
            "s3_arn": f"arn:aws:s3:::{s3_bucket_name}",
            "sharing_url": f"https://{cloudfront_domain}",
        }
    )

    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"✓ Updated {config_path}")
    except Exception as e:
        logger.warning(f"Could not update {config_path}: {e}")


def main():
    """Create/reuse S3 + CloudFront, create Tavily secret."""
    parser = argparse.ArgumentParser(
        description=(
            "DocGraph Intelligence AWS setup "
            "(shared S3/CloudFront reuse + Tavily secret)"
        )
    )
    parser.add_argument(
        "--skip-secrets",
        action="store_true",
        help="Skip Secrets Manager creation",
    )
    parser.add_argument(
        "--secrets-no-prompt",
        action="store_true",
        help="Create empty secrets without prompting for API keys",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DocGraph Intelligence — AWS setup (local app)")
    logger.info("=" * 60)
    logger.info(f"Project: {project_name}")
    logger.info(f"Region: {region}")
    logger.info(f"Account ID: {account_id}")
    logger.info(f"Shared S3 Bucket: {bucket_name}")
    logger.info(f"Shared CloudFront comment: {cloudfront_comment}")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        s3_bucket_name = create_s3_bucket()
        cloudfront_info = create_cloudfront_distribution(s3_bucket_name)

        if args.skip_secrets:
            logger.info("Skipping Secrets Manager (--skip-secrets)")
        else:
            create_secrets(skip_prompt=args.secrets_no_prompt)

        update_config(s3_bucket_name, cloudfront_info["domain"])

        elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info("Setup completed successfully")
        logger.info("=" * 60)
        logger.info(f"  S3 Bucket: {s3_bucket_name}")
        logger.info(f"  CloudFront: https://{cloudfront_info['domain']}")
        logger.info(f"  Time: {elapsed:.1f}s")
        logger.info("")
        logger.info("Run the app locally: ./run_local.sh")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Setup failed: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
