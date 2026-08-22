#!/usr/bin/env python3
"""
AWS Infrastructure Uninstaller for DocGraph Intelligence.

By default deletes nothing shared.
Shared S3 / CloudFront / tavilyapikey are retained unless explicitly requested —
same pattern as agent-skills.
"""

import argparse
import logging
import sys
import time

import boto3
from botocore.exceptions import ClientError

project_name = "docgraph"
region = "us-west-2"
cloudfront_comment = "CloudFront-for-rag-project"
oai_comment = "OAI for rag-project"

sts_client = boto3.client("sts", region_name=region)
account_id = sts_client.get_caller_identity()["Account"]

s3_client = boto3.client("s3", region_name=region)
secrets_client = boto3.client("secretsmanager", region_name=region)
cloudfront_client = boto3.client("cloudfront", region_name=region)

bucket_name = f"storage-for-rag-project-{account_id}-{region}"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def delete_secrets():
    """Delete shared Tavily secret (destructive — used by other projects too)."""
    logger.info("Deleting shared secret: tavilyapikey")

    secret_name = "tavilyapikey"
    try:
        secrets_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True,
        )
        logger.info(f"  ✓ Deleted secret: {secret_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            logger.warning(f"  Could not delete secret {secret_name}: {e}")

    logger.info("✓ Secrets deleted")


def delete_s3_buckets():
    """Delete shared S3 bucket and all objects (destructive)."""
    logger.info(f"Deleting shared S3 bucket: {bucket_name}")

    try:
        versions = s3_client.list_object_versions(Bucket=bucket_name)
        delete_keys = []
        for version in versions.get("Versions", []):
            delete_keys.append(
                {"Key": version["Key"], "VersionId": version["VersionId"]}
            )
        for marker in versions.get("DeleteMarkers", []):
            delete_keys.append(
                {"Key": marker["Key"], "VersionId": marker["VersionId"]}
            )

        for i in range(0, len(delete_keys), 1000):
            batch = delete_keys[i : i + 1000]
            s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": batch})
        if delete_keys:
            logger.info(
                f"  ✓ Deleted {len(delete_keys)} objects/versions from {bucket_name}"
            )

        s3_client.delete_bucket(Bucket=bucket_name)
        logger.info(f"  ✓ Deleted bucket: {bucket_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            logger.info(f"  Bucket {bucket_name} does not exist")
        else:
            logger.warning(f"  Could not delete bucket {bucket_name}: {e}")

    logger.info("✓ S3 buckets deleted")


def _wait_cloudfront_disabled(dist_id: str, max_wait: int = 600) -> bool:
    start = time.time()
    while time.time() - start < max_wait:
        dist = cloudfront_client.get_distribution(Id=dist_id)
        status = dist["Distribution"]["Status"]
        enabled = dist["Distribution"]["DistributionConfig"]["Enabled"]
        if status == "Deployed" and not enabled:
            return True
        logger.info(f"  Waiting for CloudFront {dist_id} to disable (status={status})...")
        time.sleep(30)
    logger.warning("  Timed out waiting for CloudFront to disable")
    return False


def delete_cloudfront_distributions():
    """Disable and delete shared CloudFront distributions."""
    logger.info(f"Deleting shared CloudFront ({cloudfront_comment})")

    try:
        distributions = cloudfront_client.list_distributions()
        items = (distributions.get("DistributionList") or {}).get("Items") or []
        for dist in items:
            if cloudfront_comment not in dist.get("Comment", ""):
                continue
            dist_id = dist["Id"]
            cfg = cloudfront_client.get_distribution_config(Id=dist_id)
            config = cfg["DistributionConfig"]
            etag = cfg["ETag"]
            if config.get("Enabled"):
                config["Enabled"] = False
                cloudfront_client.update_distribution(
                    Id=dist_id,
                    IfMatch=etag,
                    DistributionConfig=config,
                )
                logger.info(f"  Disabled CloudFront: {dist_id}")
            if not _wait_cloudfront_disabled(dist_id):
                continue
            cfg = cloudfront_client.get_distribution_config(Id=dist_id)
            cloudfront_client.delete_distribution(Id=dist_id, IfMatch=cfg["ETag"])
            logger.info(f"  ✓ Deleted CloudFront: {dist_id}")
    except ClientError as e:
        logger.warning(f"  CloudFront cleanup: {e}")


def delete_cloudfront_oai():
    """Delete shared Origin Access Identity if unused."""
    try:
        oai_list = cloudfront_client.list_cloud_front_origin_access_identities()
        for oai in oai_list.get("CloudFrontOriginAccessIdentityList", {}).get("Items", []):
            comment = oai.get("Comment", "")
            if oai_comment not in comment and "rag-project" not in comment:
                continue
            try:
                oai_cfg = cloudfront_client.get_cloud_front_origin_access_identity_config(
                    Id=oai["Id"]
                )
                cloudfront_client.delete_cloud_front_origin_access_identity(
                    Id=oai["Id"],
                    IfMatch=oai_cfg["ETag"],
                )
                logger.info(f"  ✓ Deleted OAI: {oai['Id']}")
            except ClientError as e:
                logger.warning(f"  Could not delete OAI {oai['Id']}: {e}")
    except ClientError as e:
        logger.warning(f"  OAI cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "DocGraph Intelligence AWS cleanup "
            "(shared S3 / CloudFront / tavilyapikey optional)"
        )
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument(
        "--delete-secrets",
        action="store_true",
        help="Also delete shared secret tavilyapikey",
    )
    parser.add_argument(
        "--delete-s3-bucket",
        action="store_true",
        help=f"Also delete shared S3 bucket ({bucket_name})",
    )
    parser.add_argument(
        "--delete-cloudfront",
        action="store_true",
        help=f"Also delete shared CloudFront ({cloudfront_comment})",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DocGraph Intelligence — AWS cleanup")
    logger.info("=" * 60)
    logger.info(f"Project: {project_name}")
    logger.info(f"Region: {region}")
    logger.info(f"Account ID: {account_id}")
    logger.info("=" * 60)

    if not args.yes:
        print("\nDefault: keep shared S3 / CloudFront / tavilyapikey.")
        print(
            "Pass --delete-secrets / --delete-s3-bucket / --delete-cloudfront to remove them."
        )
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Uninstallation cancelled.")
            sys.exit(0)

    start_time = time.time()
    try:
        if args.delete_secrets:
            delete_secrets()
        else:
            logger.info("[skip] Secret retained (shared): tavilyapikey")

        if args.delete_s3_bucket:
            delete_s3_buckets()
        else:
            logger.info(f"[skip] S3 bucket retained (shared): {bucket_name}")

        if args.delete_cloudfront:
            delete_cloudfront_distributions()
            delete_cloudfront_oai()
        else:
            logger.info(f"[skip] CloudFront retained (shared): {cloudfront_comment}")

        elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info("Cleanup completed")
        logger.info(f"Total time: {elapsed:.1f}s")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("Cleanup failed: %s", e)
        import traceback

        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
