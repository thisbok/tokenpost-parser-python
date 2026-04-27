"""AWS S3 Uploader - HTML 파일을 S3에 업로드합니다."""

from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Optional
from config import AWS_REGION, S3_BUCKET_NAME, S3_PREFIX


def _encode_metadata_value(value: str) -> str:
    """S3 메타데이터용으로 비 ASCII 문자를 URL 인코딩합니다."""
    if not value:
        return ""
    try:
        value.encode("ascii")
        return value[:1024]
    except UnicodeEncodeError:
        return quote(value, safe="")[:1024]


class S3Uploader:
    def __init__(
        self,
        bucket_name: str = S3_BUCKET_NAME,
        prefix: str = S3_PREFIX,
        region: str = AWS_REGION,
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client("s3", region_name=region)

    def upload_html(self, filename: str, html_content: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """HTML 콘텐츠를 S3에 업로드합니다."""
        key = f"{self.prefix}{filename}"

        extra_args = {
            "ContentType": "text/html; charset=utf-8",
        }

        if metadata:
            # S3 메타데이터는 ASCII만 허용되므로 한글 등은 URL 인코딩
            extra_args["Metadata"] = {
                k: _encode_metadata_value(str(v)) for k, v in metadata.items() if v
            }

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=html_content.encode("utf-8"),
                **extra_args,
            )
            s3_uri = f"s3://{self.bucket_name}/{key}"
            print(f"Uploaded: {s3_uri}")
            return s3_uri
        except ClientError as e:
            print(f"Error uploading {filename}: {e}")
            return None

    def upload_article(self, article_data: Dict) -> Optional[str]:
        """기사 데이터를 S3에 업로드합니다."""
        metadata = {
            "title": article_data.get("title", ""),
            "url": article_data.get("url", ""),
            "pub_date": article_data.get("pub_date", ""),
            "category": article_data.get("category", ""),
        }

        return self.upload_html(
            filename=article_data["filename"],
            html_content=article_data["raw_html"],
            metadata=metadata,
        )

    def upload_articles(self, articles: List[Dict]) -> List[str]:
        """여러 기사를 S3에 업로드합니다."""
        uploaded_uris = []

        for article in articles:
            uri = self.upload_article(article)
            if uri:
                uploaded_uris.append(uri)

        print(f"\n총 {len(uploaded_uris)}/{len(articles)}개 파일 업로드 완료")
        return uploaded_uris

    def check_exists(self, filename: str) -> bool:
        """파일이 이미 S3에 존재하는지 확인합니다."""
        key = f"{self.prefix}{filename}"
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def list_objects(self, max_keys: int = 100) -> List[str]:
        """S3 버킷의 객체 목록을 반환합니다."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix,
                MaxKeys=max_keys,
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            print(f"Error listing objects: {e}")
            return []


if __name__ == "__main__":
    uploader = S3Uploader()

    # 테스트 업로드
    test_html = "<html><body><h1>테스트</h1></body></html>"
    test_metadata = {"title": "테스트 기사", "url": "https://example.com"}

    uri = uploader.upload_html("test_article.html", test_html, test_metadata)
    if uri:
        print(f"테스트 업로드 성공: {uri}")
