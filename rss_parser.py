"""RSS Feed Parser for TokenPost"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from config import RSS_URL, REQUEST_TIMEOUT, USER_AGENT


def fetch_rss_feed(url: str = RSS_URL) -> str:
    """RSS 피드 XML 데이터를 가져옵니다."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_rss_items(xml_content: str) -> List[Dict[str, str]]:
    """RSS XML을 파싱하여 아이템 목록을 반환합니다."""
    soup = BeautifulSoup(xml_content, "xml")
    items = []

    for item in soup.find_all("item"):
        article = {
            "title": item.find("title").get_text(strip=True) if item.find("title") else "",
            "link": item.find("link").get_text(strip=True) if item.find("link") else "",
            "description": item.find("description").get_text(strip=True) if item.find("description") else "",
            "pub_date": item.find("pubDate").get_text(strip=True) if item.find("pubDate") else "",
            "category": item.find("category").get_text(strip=True) if item.find("category") else "",
        }

        if article["link"]:
            items.append(article)

    return items


def get_article_links() -> List[Dict[str, str]]:
    """RSS 피드에서 모든 기사 정보를 가져옵니다."""
    xml_content = fetch_rss_feed()
    return parse_rss_items(xml_content)


if __name__ == "__main__":
    articles = get_article_links()
    print(f"총 {len(articles)}개의 기사를 찾았습니다.\n")

    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article['title']}")
        print(f"   URL: {article['link']}")
        print(f"   날짜: {article['pub_date']}")
        print()
