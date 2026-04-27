import os
from dotenv import load_dotenv

load_dotenv()

# RSS Feed URL
RSS_URL = "https://www.tokenpost.kr/rss"

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "tokenpost-knowledge-base")
S3_PREFIX = os.getenv("S3_PREFIX", "articles/")

# Bedrock Knowledge Base Configuration
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")
DATA_SOURCE_ID = os.getenv("DATA_SOURCE_ID", "")

# Crawler Configuration
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # seconds between requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
