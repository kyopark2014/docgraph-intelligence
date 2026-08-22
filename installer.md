# AWS Infrastructure Installer

로컬 DocGraph Intelligence용으로 **공유 S3 / CloudFront / Tavily Secret**(agent-skills와 동일)을  
있으면 재사용하고, 없으면 생성합니다.

## 리소스

| 리소스 | 이름 / 식별 | 동작 |
|--------|-------------|------|
| S3 | `storage-for-rag-project-{account}-{region}` | 있으면 **재사용**, 없으면 생성 |
| CloudFront | comment `CloudFront-for-rag-project` (S3 origin) | 있으면 **재사용**, 없으면 생성 |
| Secrets | `tavilyapikey` | 있으면 **재사용**, 없으면 생성 |

## 실행

```bash
python installer.py
python installer.py --secrets-no-prompt
python installer.py --skip-secrets
```

`application/config.json`에 `s3_bucket`, `sharing_url`(CloudFront) 등을 갱신합니다.

## 삭제

```bash
# 기본: 공유 리소스 모두 유지 (삭제 없음)
python uninstaller.py --yes

# 공유 리소스까지 삭제 (다른 프로젝트에도 영향)
python uninstaller.py --yes --delete-secrets --delete-s3-bucket --delete-cloudfront
```

## 설정값 (`installer.py`)

```python
project_name = "docgraph"
region = "us-west-2"
bucket_name = f"storage-for-rag-project-{account_id}-{region}"
cloudfront_comment = "CloudFront-for-rag-project"
# secret name: tavilyapikey  (shared)
```
