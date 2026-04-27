#!/usr/bin/env python3
"""
TokenPost RSS Crawler
RSS 피드에서 기사를 수집하여 S3에 저장하고 Bedrock Knowledge Base를 동기화합니다.
"""

import argparse
import sys
from typing import List, Dict
from rss_parser import get_article_links
from html_fetcher import fetch_article
from s3_uploader import S3Uploader
from bedrock_sync import BedrockKnowledgeBaseSync
from config import REQUEST_DELAY


def crawl_articles(
    max_articles: int = 0,
    skip_existing: bool = True,
    delay: float = REQUEST_DELAY,
) -> List[Dict]:
    """RSS 피드에서 기사를 크롤링합니다."""
    print("=" * 60)
    print("TokenPost RSS Crawler")
    print("=" * 60)

    # 1. RSS 피드에서 기사 링크 가져오기
    print("\n[1/4] RSS 피드 파싱 중...")
    articles = get_article_links()
    print(f"     {len(articles)}개의 기사를 찾았습니다.")

    if max_articles > 0:
        articles = articles[:max_articles]
        print(f"     최대 {max_articles}개의 기사만 처리합니다.")

    # 2. 각 기사의 HTML 가져오기
    print(f"\n[2/4] 기사 HTML 수집 중...")
    fetched_articles = []

    for i, article in enumerate(articles, 1):
        print(f"     ({i}/{len(articles)}) {article['title'][:40]}...")
        result = fetch_article(article, delay=delay)
        if result:
            fetched_articles.append(result)

    print(f"     {len(fetched_articles)}개의 기사를 수집했습니다.")
    return fetched_articles


def upload_to_s3(articles: List[Dict], skip_existing: bool = True) -> List[str]:
    """수집한 기사를 S3에 업로드합니다."""
    print(f"\n[3/4] S3 업로드 중...")

    uploader = S3Uploader()
    uploaded_uris = []

    for i, article in enumerate(articles, 1):
        if skip_existing and uploader.check_exists(article["filename"]):
            print(f"     ({i}/{len(articles)}) 스킵 (이미 존재): {article['filename']}")
            continue

        uri = uploader.upload_article(article)
        if uri:
            uploaded_uris.append(uri)
            print(f"     ({i}/{len(articles)}) 업로드 완료: {article['filename']}")

    print(f"     {len(uploaded_uris)}개의 파일을 업로드했습니다.")
    return uploaded_uris


def sync_knowledge_base(wait_for_completion: bool = True, timeout: int = 600) -> bool:
    """Bedrock Knowledge Base를 동기화합니다."""
    print(f"\n[4/4] Bedrock Knowledge Base 동기화 중...")

    sync = BedrockKnowledgeBaseSync()

    if wait_for_completion:
        success = sync.sync_and_wait(timeout=timeout)
    else:
        job_info = sync.start_ingestion_job()
        success = job_info is not None
        if success:
            print(f"     동기화 작업이 시작되었습니다. (Job ID: {job_info.get('ingestionJobId')})")

    return success


def run_full_pipeline(
    max_articles: int = 0,
    skip_existing: bool = True,
    skip_sync: bool = False,
    wait_for_sync: bool = True,
    delay: float = REQUEST_DELAY,
) -> bool:
    """전체 파이프라인을 실행합니다."""
    try:
        # 크롤링
        articles = crawl_articles(
            max_articles=max_articles,
            skip_existing=skip_existing,
            delay=delay,
        )

        if not articles:
            print("\n수집된 기사가 없습니다.")
            return False

        # S3 업로드
        uploaded_uris = upload_to_s3(articles, skip_existing=skip_existing)

        if not uploaded_uris:
            print("\n새로 업로드된 파일이 없습니다.")
            if not skip_sync:
                print("Knowledge Base 동기화를 건너뜁니다.")
            return True

        # Knowledge Base 동기화
        if not skip_sync:
            success = sync_knowledge_base(wait_for_completion=wait_for_sync)
            if not success:
                print("\nKnowledge Base 동기화에 실패했습니다.")
                return False

        print("\n" + "=" * 60)
        print("파이프라인 완료!")
        print(f"  - 수집된 기사: {len(articles)}개")
        print(f"  - 업로드된 파일: {len(uploaded_uris)}개")
        print("=" * 60)

        return True

    except KeyboardInterrupt:
        print("\n\n작업이 사용자에 의해 중단되었습니다.")
        return False
    except Exception as e:
        print(f"\n오류 발생: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="TokenPost RSS 크롤러 - 기사를 수집하여 S3에 저장하고 Bedrock Knowledge Base를 동기화합니다."
    )

    parser.add_argument(
        "-n", "--max-articles",
        type=int,
        default=0,
        help="처리할 최대 기사 수 (0=전체, 기본값: 0)",
    )

    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="이미 존재하는 파일도 다시 업로드",
    )

    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Knowledge Base 동기화 건너뛰기",
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="동기화 완료를 기다리지 않음",
    )

    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=REQUEST_DELAY,
        help=f"요청 간 대기 시간 (초, 기본값: {REQUEST_DELAY})",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="크롤링만 수행하고 업로드/동기화 건너뛰기",
    )

    args = parser.parse_args()

    if args.dry_run:
        articles = crawl_articles(
            max_articles=args.max_articles,
            delay=args.delay,
        )
        print(f"\n[Dry Run] {len(articles)}개의 기사를 수집했습니다.")
        for article in articles[:5]:
            print(f"  - {article['title']}")
        if len(articles) > 5:
            print(f"  ... 외 {len(articles) - 5}개")
        return

    success = run_full_pipeline(
        max_articles=args.max_articles,
        skip_existing=not args.no_skip,
        skip_sync=args.skip_sync,
        wait_for_sync=not args.no_wait,
        delay=args.delay,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
