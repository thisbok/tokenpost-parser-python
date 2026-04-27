"""HTML Fetcher - URL에 접속하여 HTML 데이터를 가져옵니다."""

import time
import hashlib
import re
from datetime import datetime
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
from config import REQUEST_TIMEOUT, REQUEST_DELAY, USER_AGENT


def fetch_html(url: str) -> Optional[str]:
    """URL에서 HTML 콘텐츠를 가져옵니다."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_article_content(html: str) -> Dict[str, str]:
    """HTML에서 기사 본문과 메타데이터를 추출합니다."""
    soup = BeautifulSoup(html, "lxml")

    # 메타데이터 추출
    title = ""
    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        title = title_tag.get("content", "")
    elif soup.find("title"):
        title = soup.find("title").get_text(strip=True)

    description = ""
    desc_tag = soup.find("meta", property="og:description")
    if desc_tag:
        description = desc_tag.get("content", "")

    # 기사 본문 추출 (TokenPost 구조에 맞게)
    content = ""
    article_body = soup.find("div", class_="article-body") or soup.find("article") or soup.find("div", class_="content")

    if article_body:
        # 불필요한 태그 제거
        for tag in article_body.find_all(["script", "style", "iframe", "ins", "aside"]):
            tag.decompose()
        content = article_body.get_text(separator="\n", strip=True)

    return {
        "title": title,
        "description": description,
        "content": content,
        "raw_html": html,
    }


def generate_filename(url: str, title: str = "") -> str:
    """URL과 제목을 기반으로 고유한 파일명을 생성합니다."""
    # URL에서 article ID 추출 시도
    article_id_match = re.search(r"/(\d+)/?$", url)
    if article_id_match:
        article_id = article_id_match.group(1)
    else:
        # URL 해시 사용
        article_id = hashlib.md5(url.encode()).hexdigest()[:8]

    # 타임스탬프
    timestamp = datetime.now().strftime("%Y%m%d")

    # 제목 정리 (파일명에 사용 가능한 문자만)
    safe_title = re.sub(r"[^\w\s가-힣-]", "", title)[:30].strip()
    safe_title = re.sub(r"\s+", "_", safe_title)

    return f"{timestamp}_{article_id}_{safe_title}.html"


def fetch_article(article_info: Dict[str, str], delay: float = REQUEST_DELAY) -> Optional[Dict]:
    """기사 정보를 받아 HTML을 가져오고 처리합니다."""
    url = article_info.get("link", "")
    if not url:
        return None

    html = fetch_html(url)
    if not html:
        return None

    extracted = extract_article_content(html)
    filename = generate_filename(url, article_info.get("title", ""))

    time.sleep(delay)  # Rate limiting

    return {
        "url": url,
        "title": article_info.get("title", extracted["title"]),
        "pub_date": article_info.get("pub_date", ""),
        "category": article_info.get("category", ""),
        "content": extracted["content"],
        "description": extracted["description"],
        "raw_html": extracted["raw_html"],
        "filename": filename,
    }


if __name__ == "__main__":
    # 테스트
    test_article = {
        "title": "테스트 기사",
        "link": "https://www.tokenpost.kr/article-210886",
    }

    result = fetch_article(test_article)
    if result:
        print(f"제목: {result['title']}")
        print(f"파일명: {result['filename']}")
        print(f"본문 길이: {len(result['content'])} 글자")
