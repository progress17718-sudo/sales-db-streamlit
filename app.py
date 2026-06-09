from __future__ import annotations

import io
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
from rapidfuzz import fuzz, process


APP_TITLE = "영업 DB 자동 수집 웹툴"
REQUEST_TIMEOUT = 25
SERPAPI_MAX_RETRIES = 2
FUZZY_BRAND_THRESHOLD = 88
AI_REQUEST_TIMEOUT = 30
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

INDUSTRY_OPTIONS = [
    "뷰티",
    "식품",
    "패션",
    "생활용품",
    "반려동물",
    "유아",
    "병원",
    "프랜차이즈",
]

KEYWORD_PRESETS = {
    "뷰티": ["화장품 브랜드 공식몰", "스킨케어 브랜드 공식 홈페이지", "바디케어 브랜드 공식몰", "뷰티 브랜드 자사몰", "화장품 브랜드 제휴문의"],
    "식품": [
        "건강식품 브랜드 공식몰",
        "밀키트 브랜드 공식몰",
        "간편식 브랜드 공식몰",
        "식품 브랜드 자사몰",
        "식품 브랜드 공식 홈페이지",
        "프리미엄 식품 브랜드 공식몰",
        "다이어트 식품 브랜드 공식몰",
        "냉동식품 브랜드 공식몰",
        "식품 브랜드 제휴문의",
    ],
    "패션": [
        "여성의류 브랜드 공식몰",
        "디자이너 브랜드 공식몰",
        "패션 브랜드 자사몰",
        "의류 브랜드 공식 홈페이지",
        "자체제작 의류 브랜드 공식몰",
        "스트릿 패션 브랜드 공식몰",
        "남성의류 브랜드 공식몰",
        "컨템포러리 브랜드 공식몰",
        "패션 브랜드 제휴문의",
        "의류 브랜드 자사몰",
    ],
    "생활용품": [
        "주방용품 브랜드 공식몰",
        "욕실용품 브랜드 공식몰",
        "세제 브랜드 공식몰",
        "청소용품 브랜드 공식몰",
        "수납용품 브랜드 공식몰",
        "홈리빙 브랜드 자사몰",
        "생활잡화 브랜드 공식몰",
        "인테리어 소품 브랜드 공식몰",
        "생활용품 브랜드 제휴문의",
    ],
    "반려동물": ["반려동물 용품 브랜드 공식몰", "강아지 간식 브랜드 공식 홈페이지", "펫 브랜드 자사몰", "펫푸드 브랜드 공식 홈페이지"],
    "유아": [
        "유아용품 브랜드 공식몰",
        "아기용품 브랜드 공식몰",
        "육아용품 브랜드 공식몰",
        "유아식 브랜드 공식몰",
        "아기화장품 브랜드 공식몰",
        "유아복 브랜드 공식몰",
        "유아 브랜드 자사몰",
        "유아용품 브랜드 제휴문의",
    ],
    "병원": ["피부과 공식 홈페이지", "성형외과 공식 홈페이지", "치과 공식 홈페이지", "한의원 공식 홈페이지"],
    "프랜차이즈": [
        "프랜차이즈 브랜드 공식 홈페이지",
        "외식 프랜차이즈 공식 홈페이지",
        "카페 프랜차이즈 공식 홈페이지",
        "치킨 프랜차이즈 공식 홈페이지",
        "창업문의 프랜차이즈 브랜드",
        "가맹문의 프랜차이즈 브랜드",
        "프랜차이즈 브랜드 제휴문의",
    ],
}

BRAND_COLUMN_CANDIDATES = [
    "브랜드명",
    "업체명",
    "회사명",
    "상호명",
    "브랜드",
    "금지업체명",
    "광고주 업체명",
    "광고주업체명",
]

URL_COLUMN_CANDIDATES = [
    "도메인",
    "URL",
    "url",
    "사이트",
    "사이트주소",
    "홈페이지",
    "공식URL",
    "공식 URL",
]

CONTACT_COLUMN_CANDIDATES = ["연락처", "전화번호", "대표번호"]
HEADER_KEYWORDS = ["광고주 업체명", "사이트", "연락처", "일자", "구분"]
HEADER_SCAN_LIMIT = 30

BAD_RESULT_KEYWORDS = [
    "기사",
    "보도",
    "보도자료",
    "언론",
    "매체",
    "인터뷰",
    "칼럼",
    "기획기사",
    "인터넷기사",
    "신문",
    "경제지",
    "매거진",
    "분석",
    "보고서",
    "리포트",
    "시장조사",
    "시장 분석",
    "트렌드",
    "동향",
    "산업동향",
    "통계",
    "자료",
    "PDF",
    "pdf",
    "연구",
    "논문",
    "사례",
    "추천",
    "순위",
    "랭킹",
    "후기",
    "리뷰",
    "이벤트",
    "쿠폰",
    "할인",
    "프로모션",
    "기획전",
    "채용",
    "구인",
    "구직",
    "잡코리아",
    "사람인",
    "원티드",
    "인크루트",
    "뉴스",
    "블로그",
    "카페",
    "Threads",
    "threads",
    "스레드",
    "쓰레드",
    "인스타그램",
    "Instagram",
    "페이스북",
    "Facebook",
    "트위터",
    "Twitter",
    "TikTok",
    "틱톡",
    "커뮤니티",
    "게시글",
    "댓글",
    "포럼",
    "후기글",
    "유저",
    "네티즌",
    "SNS",
    "sns",
    "유튜브",
    "youtube",
    "위키",
    "나무위키",
    "github",
    "news",
    "article",
    "media",
    "press",
    "report",
    "research",
    "trend",
    "analysis",
    "magazine",
    "ranking",
    "review",
    "event",
    "coupon",
    "promotion",
    "recruit",
    "job",
]

BAD_RESULT_DOMAINS = [
    "news.naver.com",
    "n.news.naver.com",
    "m.news.naver.com",
    "news.daum.net",
    "v.daum.net",
    "media.naver.com",
    "blog.naver.com",
    "cafe.naver.com",
    "chosun.com",
    "joins.com",
    "joongang.co.kr",
    "donga.com",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "etnews.com",
    "fnnews.com",
    "newsis.com",
    "yna.co.kr",
    "kmib.co.kr",
    "khan.co.kr",
    "hani.co.kr",
    "mt.co.kr",
    "edaily.co.kr",
    "zdnet.co.kr",
    "bloter.net",
    "bizwatch.co.kr",
    "consumer.go.kr",
    "kca.go.kr",
    "data.go.kr",
    "kosis.kr",
    "stat.go.kr",
    "jobkorea.co.kr",
    "saramin.co.kr",
    "wanted.co.kr",
    "incruit.com",
    "albamon.com",
    "threads.net",
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
    "reddit.com",
    "dcinside.com",
    "fmkorea.com",
    "theqoo.net",
    "instiz.net",
    "pann.nate.com",
    "clien.net",
    "ppomppu.co.kr",
    "ruliweb.com",
    "todayhumor.co.kr",
    "slrclub.com",
    "namu.wiki",
    "wikipedia.org",
    "github.com",
    "tistory.com",
    "brunch.co.kr",
]

FASHION_BAD_DOMAINS = [
    "consumer.go.kr",
    "kca.go.kr",
    "e-landmall.co.kr",
    "elandmall.co.kr",
    "elandmall.com",
    "e-land.co.kr",
    "musinsa.com",
    "29cm.co.kr",
    "wconcept.co.kr",
    "zigzag.kr",
    "a-bly.com",
    "brich.co.kr",
    "halfclub.com",
    "lotteon.com",
    "ssg.com",
    "gmarket.co.kr",
    "auction.co.kr",
    "11st.co.kr",
    "coupang.com",
    "shopping.naver.com",
    "brand.naver.com",
    "smartstore.naver.com",
]

FASHION_BAD_KEYWORDS = [
    "소비생활정보망",
    "소비자정보",
    "소비자원",
    "한국소비자원",
    "종합몰",
    "이랜드몰",
    "이랜드",
    "브랜드관",
    "입점",
    "입점몰",
    "편집샵",
    "셀렉트샵",
    "브랜드 모음",
    "브랜드 추천",
    "인기 브랜드",
    "입점 브랜드",
    "전체 브랜드",
    "쇼핑정보",
    "가격비교",
    "상품정보",
    "상품 검색",
    "상품검색",
    "기획전",
    "BEST",
    "베스트",
    "platform",
    "select shop",
]

PLATFORM_DOMAINS = [
    "coupang.com",
    "shopping.naver.com",
    "gmarket.co.kr",
    "auction.co.kr",
    "11st.co.kr",
    "lotteon.com",
    "ssg.com",
    "e-landmall.co.kr",
    "elandmall.co.kr",
    "elandmall.com",
    "e-land.co.kr",
    "musinsa.com",
    "29cm.co.kr",
    "wconcept.co.kr",
    "zigzag.kr",
    "a-bly.com",
    "brich.co.kr",
    "halfclub.com",
]

BLOG_CAFE_COMMUNITY_DOMAINS = [
    "blog.naver.com",
    "cafe.naver.com",
    "tistory.com",
    "brunch.co.kr",
    "threads.net",
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
    "reddit.com",
    "dcinside.com",
    "fmkorea.com",
    "theqoo.net",
    "instiz.net",
    "pann.nate.com",
    "clien.net",
    "ppomppu.co.kr",
    "ruliweb.com",
    "todayhumor.co.kr",
    "slrclub.com",
]
SOCIAL_COMMUNITY_KEYWORDS = [
    "Threads",
    "threads",
    "스레드",
    "쓰레드",
    "인스타그램",
    "Instagram",
    "페이스북",
    "Facebook",
    "트위터",
    "Twitter",
    "TikTok",
    "틱톡",
    "커뮤니티",
    "게시글",
    "댓글",
    "포럼",
    "후기글",
    "유저",
    "네티즌",
    "SNS",
    "sns",
]

NEWS_DOMAINS = [
    "news.naver.com",
    "n.news.naver.com",
    "m.news.naver.com",
    "news.daum.net",
    "v.daum.net",
    "media.naver.com",
    "chosun.com",
    "joins.com",
    "joongang.co.kr",
    "donga.com",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "etnews.com",
    "fnnews.com",
    "newsis.com",
    "yna.co.kr",
    "kmib.co.kr",
    "khan.co.kr",
    "hani.co.kr",
    "mt.co.kr",
    "edaily.co.kr",
    "zdnet.co.kr",
    "bloter.net",
    "bizwatch.co.kr",
]

INFO_PUBLIC_DOMAINS = ["consumer.go.kr", "kca.go.kr", "data.go.kr", "kosis.kr", "stat.go.kr"]
REPORT_KEYWORDS = ["분석", "보고서", "리포트", "트렌드", "동향", "시장조사", "통계", "자료", "연구", "논문", "report", "research", "trend", "analysis"]
NEWS_KEYWORDS = ["기사", "뉴스", "보도", "보도자료", "언론", "매체", "인터뷰", "칼럼", "기획기사", "인터넷기사", "신문", "경제지", "매거진", "news", "article", "media", "press", "magazine"]
QUERY_EXCLUSION_INDUSTRIES = {"생활용품", "유아", "식품", "프랜차이즈", "패션"}
QUERY_EXCLUSION_TERMS = ["뉴스", "기사", "보도자료", "보고서", "리포트", "트렌드", "동향", "분석", "통계", "자료", "채용", "블로그", "카페", "threads", "인스타그램", "커뮤니티", "게시글", "SNS"]

BRAND_TITLE_NOISE = [
    "공식 홈페이지",
    "공식홈페이지",
    "공식 사이트",
    "공식사이트",
    "공식몰",
    "자사몰",
    "온라인몰",
    "쇼핑몰",
    "브랜드몰",
    "회사소개",
    "제휴문의",
    "네이버 지도",
    "네이버지도",
    "브랜드",
    "스토어",
    "STORE",
    "Official",
    "공식",
    "홈페이지",
    "채용",
    "이벤트",
    "뉴스",
    "블로그",
    "카페",
]


@dataclass(frozen=True)
class SearchResult:
    brand_name: str
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ForbiddenSheetInfo:
    header_row: int | None
    brand_column: str
    url_column: str
    contact_column: str


@dataclass(frozen=True)
class CollectionStats:
    raw_count: int
    quality_excluded_count: int
    quality_excluded_rows: list[dict[str, str]]


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def get_config_value(key: str) -> str:
    env_value = os.getenv(key, "").strip()
    if env_value:
        return env_value
    try:
        secret_value = st.secrets.get(key, "")
    except Exception:
        return ""
    return clean_text(secret_value)


def normalize_column_name(value: object) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", clean_text(value)).lower()


def normalize_brand(value: object) -> str:
    text = normalize_column_name(value)
    text = re.sub(r"(공식몰|공식홈페이지|공식사이트|자사몰|홈페이지|브랜드|주식회사|주식|회사|㈜)", "", text)
    return text.strip()


def extract_domain(url: object) -> str:
    text = clean_text(url)
    if not text:
        return ""
    text = re.sub(r"^[<('\"\[]+|[>)'\"\],.]+$", "", text)
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def normalize_site(url: object) -> str:
    return extract_domain(url)


def domain_matches(domain: str, blocked_domain: str) -> bool:
    domain = extract_domain(domain)
    blocked_domain = extract_domain(blocked_domain)
    return bool(domain and blocked_domain and (domain == blocked_domain or domain.endswith(f".{blocked_domain}")))


def fallback_brand_from_url(url: object) -> str:
    text = clean_text(url)
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = extract_domain(url)
    if domain in {"smartstore.naver.com", "brand.naver.com"}:
        path_part = next((part for part in parsed.path.split("/") if part), "")
        if path_part:
            return clean_text(re.sub(r"[^0-9A-Za-z가-힣_-]", "", path_part))[:40]
    first_label = domain.split(".")[0] if domain else ""
    return clean_text(re.sub(r"[^0-9A-Za-z가-힣_-]", "", first_label))[:40]


def clean_brand_title(title: object, url: object = "") -> str:
    text = clean_text(title)
    text = re.split(r"\s*(?:\||::|>|:|-)\s*", text, maxsplit=1)[0]
    for noise in BRAND_TITLE_NOISE:
        text = re.sub(re.escape(noise), "", text, flags=re.IGNORECASE)
    text = clean_text(text).strip(" -|:｜–—:>")
    text = re.sub(r"\s{2,}", " ", text)
    if not text or len(text) > 40 or len(normalize_column_name(text)) < 2:
        return fallback_brand_from_url(url)
    return text[:40]


def split_url_values(value: object) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    urls: list[str] = []
    for line in text.split("\n"):
        line = clean_text(line)
        if not line:
            continue
        matches = re.findall(r"https?://[^\s,;]+", line, flags=re.IGNORECASE)
        urls.extend(matches or [line])
    return dedupe_keep_order(urls)


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        key = clean_text(item).lower()
        if key and key not in seen:
            seen.add(key)
            output.append(item)
    return output


def build_search_query(keyword: str, industry: str = "") -> str:
    excluded_sites = ["instagram.com", "facebook.com", *BAD_RESULT_DOMAINS]
    if industry == "패션":
        excluded_sites.extend(FASHION_BAD_DOMAINS)
    exclusions = " ".join(f"-site:{domain}" for domain in dedupe_keep_order(excluded_sites))
    excluded_terms = ""
    if industry in QUERY_EXCLUSION_INDUSTRIES:
        excluded_terms = " ".join(f"-{term}" for term in QUERY_EXCLUSION_TERMS)
    return f"{keyword} {excluded_terms} {exclusions}".strip()


def search_serpapi(keyword: str, limit: int, industry: str = "") -> list[SearchResult]:
    api_key = get_config_value("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY가 환경변수 또는 Streamlit secrets에 설정되어 있지 않습니다.")

    params = {
        "engine": "google",
        "q": build_search_query(keyword, industry),
        "api_key": api_key,
        "hl": "ko",
        "gl": "kr",
        "num": min(max(limit, 1), 10),
    }

    payload = fetch_serpapi_payload(params)

    results: list[SearchResult] = []
    for item in payload.get("organic_results", [])[:limit]:
        title = clean_text(item.get("title", ""))
        url = clean_text(item.get("link", ""))
        snippet = clean_text(item.get("snippet", ""))
        if not title or not url:
            continue
        results.append(
            SearchResult(
                brand_name=clean_brand_title(title, url),
                title=title,
                url=url,
                snippet=snippet,
            )
        )
    return results


def fetch_serpapi_payload(params: dict[str, object]) -> dict:
    for attempt in range(SERPAPI_MAX_RETRIES + 1):
        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as exc:
            if attempt < SERPAPI_MAX_RETRIES:
                st.info("검색 API 응답 대기 중입니다. 잠시만 기다려주세요.")
                time.sleep(1)
                continue
            raise RuntimeError("검색 API 응답이 지연되었습니다. 잠시 후 다시 시도해주세요.") from exc
        except requests.RequestException as exc:
            raise RuntimeError("검색 API 호출에 실패했습니다. 잠시 후 다시 시도해주세요.") from exc
        except ValueError as exc:
            raise RuntimeError("검색 API 응답을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.") from exc

    raise RuntimeError("검색 API 응답이 지연되었습니다. 잠시 후 다시 시도해주세요.")


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def combined_result_text(result: SearchResult) -> str:
    return f"{result.title} {result.url} {result.snippet}"


def is_brand_like_domain(domain: str) -> bool:
    if not domain:
        return False
    blocked_domains = BAD_RESULT_DOMAINS + PLATFORM_DOMAINS + INFO_PUBLIC_DOMAINS + BLOG_CAFE_COMMUNITY_DOMAINS
    if any(domain_matches(domain, blocked) for blocked in blocked_domains):
        return False
    first_label = domain.split(".")[0]
    if first_label in {"shop", "shopping", "mall", "store", "brand", "market", "www"}:
        return False
    return len(first_label) >= 3


def quality_score(result: SearchResult) -> int:
    domain = extract_domain(result.url)
    parsed = urlparse(result.url if "://" in result.url else f"https://{result.url}")
    path = parsed.path.lower()
    path_parts = [part for part in path.split("/") if part]
    target_text = combined_result_text(result).lower()
    score = 0

    if contains_any(f"{result.title} {result.snippet}", ["공식몰", "공식 홈페이지", "자사몰", "브랜드 공식", "제휴문의"]):
        score += 2
    if domain and not any(domain_matches(domain, blocked) for blocked in BAD_RESULT_DOMAINS + PLATFORM_DOMAINS):
        score += 2
    if len(path_parts) <= 1 or len(path) <= 25:
        score += 1
    if 2 <= len(normalize_column_name(clean_brand_title(result.title, result.url))) <= 20:
        score += 1

    if contains_any(target_text, ["기사", "뉴스", "보고서", "분석", "트렌드", "리포트", "news", "report", "analysis", "trend"]):
        score -= 5
    if contains_any(target_text, ["채용", "구인", "잡코리아", "사람인", "recruit", "job"]):
        score -= 5
    if any(domain_matches(domain, blocked) for blocked in BLOG_CAFE_COMMUNITY_DOMAINS):
        score -= 5
    if contains_any(target_text, ["추천", "순위", "랭킹", "후기", "리뷰", "ranking", "review"]):
        score -= 4
    if contains_any(target_text, ["이벤트", "쿠폰", "프로모션", "기획전", "event", "coupon", "promotion"]):
        score -= 3
    if any(domain_matches(domain, blocked) for blocked in PLATFORM_DOMAINS):
        score -= 4
    if contains_any(path, ["collection", "category", "product", "best", "ranking", "event"]):
        score -= 2

    return score


def exclusion_reason(result: SearchResult, industry: str) -> str:
    domain = extract_domain(result.url)
    target_text = combined_result_text(result)
    if any(domain_matches(domain, blocked_domain) for blocked_domain in NEWS_DOMAINS):
        return "제외됨: 뉴스 도메인"
    if any(domain_matches(domain, blocked_domain) for blocked_domain in INFO_PUBLIC_DOMAINS):
        return "제외됨: 정보성/공공기관 사이트"
    if any(domain_matches(domain, blocked_domain) for blocked_domain in BLOG_CAFE_COMMUNITY_DOMAINS):
        return "제외됨: SNS/커뮤니티/블로그 도메인"
    if any(domain_matches(domain, blocked_domain) for blocked_domain in BAD_RESULT_DOMAINS):
        return "제외됨: 제외 도메인"
    if contains_any(target_text, SOCIAL_COMMUNITY_KEYWORDS):
        return "제외됨: SNS/커뮤니티 키워드 포함"
    if contains_any(target_text, NEWS_KEYWORDS):
        return "제외됨: 뉴스/기사 키워드 포함"
    if contains_any(target_text, REPORT_KEYWORDS):
        return "제외됨: 보고서/분석 키워드 포함"
    if contains_any(target_text, BAD_RESULT_KEYWORDS):
        return "제외됨: 품질 제외 키워드 포함"
    if industry == "패션":
        if any(domain_matches(domain, blocked_domain) for blocked_domain in FASHION_BAD_DOMAINS):
            if any(domain_matches(domain, blocked_domain) for blocked_domain in INFO_PUBLIC_DOMAINS):
                return "제외됨: 정보성/공공기관 사이트"
            return "제외됨: 패션 종합몰/플랫폼"
        if contains_any(target_text, FASHION_BAD_KEYWORDS):
            return "제외됨: 패션 종합몰/플랫폼"
        official_signal = contains_any(f"{result.title} {result.snippet}", ["공식몰", "공식 홈페이지", "자사몰", "브랜드 공식"])
        if not official_signal and not is_brand_like_domain(domain):
            return "제외됨: 패션 공식몰 기준 미달"
    if quality_score(result) < 1:
        return "제외됨: 품질 점수 미달"
    return ""


def is_low_quality_result(result: SearchResult, industry: str) -> bool:
    return bool(exclusion_reason(result, industry))


def collect_brand_candidates(industry: str, target_count: int) -> tuple[pd.DataFrame, CollectionStats]:
    rows: list[dict[str, str]] = []
    excluded_rows: list[dict[str, str]] = []
    raw_count = 0
    quality_excluded_count = 0
    per_keyword_limit = max(1, min(10, target_count))

    for keyword in KEYWORD_PRESETS[industry]:
        if len(rows) >= target_count:
            break
        remaining = target_count - len(rows)
        results = search_serpapi(keyword, min(per_keyword_limit, remaining), industry)
        raw_count += len(results)

        for result in results:
            reason = exclusion_reason(result, industry)
            if reason:
                quality_excluded_count += 1
                excluded_rows.append(
                    {
                        "제외사유": reason,
                        "브랜드명": result.brand_name or clean_brand_title(result.title, result.url),
                        "제목": result.title,
                        "사이트": result.url,
                    }
                )
                continue
            domain = extract_domain(result.url)
            rows.append(
                {
                    "업종": industry,
                    "브랜드명": result.brand_name or clean_brand_title(result.title, result.url),
                    "사이트": result.url,
                    "도메인": domain,
                    "수집출처": "SerpAPI",
                    "검색키워드": keyword,
                }
            )
            if len(rows) >= target_count:
                break

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["도메인", "브랜드명"]).reset_index(drop=True)
    return df, CollectionStats(
        raw_count=raw_count,
        quality_excluded_count=quality_excluded_count,
        quality_excluded_rows=excluded_rows,
    )


def to_google_sheet_csv_url(sheet_url: str) -> str:
    sheet_url = sheet_url.strip()
    if "output=csv" in sheet_url or sheet_url.endswith(".csv"):
        return sheet_url

    match = re.search(r"/spreadsheets/d/([^/]+)", sheet_url)
    if not match:
        return sheet_url

    sheet_id = match.group(1)
    gid_match = re.search(r"gid=(\d+)", sheet_url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def read_csv_with_encoding_fallback(csv_url: str) -> tuple[pd.DataFrame, str, str]:
    response = requests.get(csv_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    candidates: list[tuple[str, str]] = []
    response.encoding = "utf-8"
    candidates.append(("utf-8", response.text))
    for encoding in ["utf-8-sig", "cp949"]:
        try:
            candidates.append((encoding, response.content.decode(encoding)))
        except UnicodeDecodeError:
            continue

    best_df = pd.DataFrame()
    best_encoding = ""
    best_score = -1
    best_text = ""
    for encoding, text in candidates:
        try:
            df = pd.read_csv(io.StringIO(text), header=None, dtype=str, keep_default_na=False, engine="python").fillna("")
        except Exception:
            continue
        score = korean_text_score(text, df)
        if score > best_score:
            best_df = df
            best_encoding = encoding
            best_score = score
            best_text = text

    warning = ""
    if best_text and looks_like_broken_korean(best_text):
        warning = "Google Sheet 한글 인코딩을 정상적으로 읽지 못했을 수 있습니다."
    return best_df, best_encoding, warning


def korean_text_score(text: str, df: pd.DataFrame) -> int:
    header_index, _ = find_forbidden_header_row(df)
    header_bonus = 10000 if header_index is not None else 0
    keyword_hits = sum(text.count(keyword) for keyword in HEADER_KEYWORDS + BRAND_COLUMN_CANDIDATES + URL_COLUMN_CANDIDATES)
    hangul_count = len(re.findall(r"[가-힣]", text))
    broken_count = len(re.findall(r"[�ÃÂ]|[ìíîïêëð]", text))
    return header_bonus + keyword_hits * 100 + hangul_count - broken_count * 50


def looks_like_broken_korean(text: str) -> bool:
    broken_count = len(re.findall(r"[�ÃÂ]|[ìíîïêëð]", text))
    hangul_count = len(re.findall(r"[가-힣]", text))
    return broken_count > max(3, hangul_count)


def find_forbidden_header_row(raw_df: pd.DataFrame) -> tuple[int | None, list[str]]:
    for index, row in raw_df.head(HEADER_SCAN_LIMIT).iterrows():
        values = [clean_text(value) for value in row.tolist()]
        normalized_values = [normalize_column_name(value) for value in values if value]
        matches = sum(
            1
            for keyword in HEADER_KEYWORDS
            if any(normalize_column_name(keyword) in value for value in normalized_values)
        )
        if matches >= 2:
            return int(index), values
    return None, []


def find_column(header_values: list[str], candidates: list[str]) -> str:
    candidate_keys = [normalize_column_name(candidate) for candidate in candidates]
    for value in header_values:
        key = normalize_column_name(value)
        if any(candidate_key == key or candidate_key in key for candidate_key in candidate_keys):
            return value
    return ""


def make_unique_columns(header_values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    columns = []
    for index, value in enumerate(header_values, start=1):
        base = clean_text(value) or f"빈컬럼{index}"
        counts[base] = counts.get(base, 0) + 1
        columns.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return columns


def load_forbidden_sheet(sheet_url: str) -> tuple[pd.DataFrame, ForbiddenSheetInfo, str, str]:
    empty = pd.DataFrame(columns=["브랜드명", "도메인", "연락처"])
    empty_info = ForbiddenSheetInfo(header_row=None, brand_column="", url_column="", contact_column="")
    if not sheet_url:
        return empty, empty_info, "", ""

    csv_url = to_google_sheet_csv_url(sheet_url)
    raw_df, encoding, encoding_warning = read_csv_with_encoding_fallback(csv_url)
    if raw_df.empty:
        return empty, empty_info, encoding, "Google Sheet에서 읽어온 데이터가 비어 있습니다."

    header_index, header_values = find_forbidden_header_row(raw_df)
    if header_index is None:
        return empty, empty_info, encoding, "영업금지 리스트 헤더를 찾지 못했습니다. 광고주 업체명/사이트/연락처 행을 확인해주세요."

    brand_column = find_column(header_values, BRAND_COLUMN_CANDIDATES)
    url_column = find_column(header_values, URL_COLUMN_CANDIDATES)
    contact_column = find_column(header_values, CONTACT_COLUMN_CANDIDATES)
    info = ForbiddenSheetInfo(
        header_row=header_index + 1,
        brand_column=brand_column,
        url_column=url_column,
        contact_column=contact_column,
    )

    if not brand_column and not url_column:
        return empty, info, encoding, "영업금지 리스트에서 브랜드명 또는 사이트로 사용할 컬럼을 찾을 수 없습니다."

    data_df = raw_df.iloc[header_index + 1 :].copy()
    data_df.columns = make_unique_columns(header_values)
    forbidden = normalize_forbidden_rows(data_df, brand_column, url_column, contact_column)
    return forbidden, info, encoding, encoding_warning


def normalize_forbidden_rows(data_df: pd.DataFrame, brand_column: str, url_column: str, contact_column: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for _, row in data_df.iterrows():
        brand = clean_text(row.get(brand_column, "")) if brand_column else ""
        contact = clean_text(row.get(contact_column, "")) if contact_column else ""
        url_values = split_url_values(row.get(url_column, "")) if url_column else []
        domains = [extract_domain(value) for value in url_values]
        domains = [domain for domain in dedupe_keep_order(domains) if domain] or [""]

        for domain in domains:
            if brand or domain:
                rows.append({"브랜드명": brand, "도메인": domain, "연락처": contact})

    return pd.DataFrame(rows, columns=["브랜드명", "도메인", "연락처"]).fillna("")


def apply_forbidden_filter(candidates: pd.DataFrame, forbidden: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if candidates.empty:
        return candidates.copy(), 0

    forbidden = forbidden.copy().fillna("")
    forbidden_brands = {
        normalize_brand(value)
        for value in forbidden["브랜드명"].astype(str)
        if normalize_brand(value)
    }
    forbidden_domains = {
        extract_domain(value)
        for value in forbidden["도메인"].astype(str)
        if clean_text(value)
    }

    rows: list[dict[str, object]] = []
    excluded_count = 0
    for _, row in candidates.iterrows():
        brand = clean_text(row["브랜드명"])
        brand_norm = normalize_brand(brand)
        domain = extract_domain(row["도메인"])

        if (domain and domain in forbidden_domains) or (brand_norm and brand_norm in forbidden_brands):
            excluded_count += 1
            continue

        status = "사용가능"
        similar_brand = ""
        similarity = 0
        if brand_norm and forbidden_brands:
            matched = process.extractOne(brand_norm, forbidden_brands, scorer=fuzz.ratio)
            if matched and matched[1] >= FUZZY_BRAND_THRESHOLD:
                status = "확인필요"
                similar_brand = matched[0]
                similarity = int(matched[1])

        enriched = row.to_dict()
        enriched.update({"상태": status, "유사금지브랜드": similar_brand, "유사도": similarity})
        rows.append(enriched)

    return pd.DataFrame(rows), excluded_count


def current_collection_date() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()


def prepare_output_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    output = pd.DataFrame(index=df.index)
    output["상태"] = df["상태"] if "상태" in df else ""
    output["업종"] = df["업종"] if "업종" in df else ""
    output["브랜드명"] = df["브랜드명"] if "브랜드명" in df else ""
    output["사이트"] = df["사이트"] if "사이트" in df else ""
    output["이메일"] = ""
    output["전화번호"] = ""
    output["수집출처"] = df["수집출처"] if "수집출처" in df else ""
    output["수집일"] = current_collection_date()
    return output.fillna("")


def extract_json_array(text: str) -> list[dict[str, object]]:
    text = clean_text(text)
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.IGNORECASE).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) else []


def extract_openai_text(payload: dict[str, object]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    texts: list[str] = []
    for item in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if isinstance(content, dict):
                value = content.get("text") or content.get("output_text")
                if isinstance(value, str):
                    texts.append(value)

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                texts.append(message["content"])

    return "\n".join(texts)


def request_ai_judgments(records: list[dict[str, str]]) -> list[dict[str, object]]:
    api_key = get_config_value("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 환경변수 또는 Streamlit secrets에 설정되어 있지 않습니다.")

    model = get_config_value("OPENAI_MODEL") or "gpt-4o-mini"
    prompt = (
        "아래 영업 DB 후보가 브랜드/업체 공식몰 또는 자사몰 후보로 적절한지 판단하세요.\n"
        "기존 결과를 삭제하거나 바꾸지 않고 참고용 판단만 합니다.\n"
        "각 항목마다 index, ai_judgment, ai_reason 키를 가진 JSON 배열만 반환하세요.\n"
        "ai_judgment 값은 공식몰 가능성 높음, 확인필요, 부적합 의심 중 하나만 사용하세요.\n"
        f"후보 목록: {records}"
    )
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": "너는 영업 DB 후보의 공식 사이트 적합성을 보수적으로 분류하는 검수자입니다.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=AI_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return extract_json_array(extract_openai_text(response.json()))


def add_ai_judgment_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    records = []
    for index, row in df.reset_index(drop=True).iterrows():
        records.append(
            {
                "index": int(index),
                "상태": clean_text(row.get("상태", "")),
                "업종": clean_text(row.get("업종", "")),
                "브랜드명": clean_text(row.get("브랜드명", "")),
                "사이트": clean_text(row.get("사이트", "")),
                "수집출처": clean_text(row.get("수집출처", "")),
            }
        )

    ai_rows = request_ai_judgments(records)
    if not ai_rows:
        raise RuntimeError("AI 판단 응답을 처리하지 못했습니다.")
    judgments: dict[int, dict[str, str]] = {}
    for item in ai_rows:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        judgments[index] = {
            "AI 판단": clean_text(item.get("ai_judgment", "")),
            "AI 판단 사유": clean_text(item.get("ai_reason", "")),
        }

    output = df.copy()
    output["AI 판단"] = ""
    output["AI 판단 사유"] = ""
    for position, frame_index in enumerate(output.index):
        row_judgment = judgments.get(position, {})
        output.at[frame_index, "AI 판단"] = row_judgment.get("AI 판단", "")
        output.at[frame_index, "AI 판단 사유"] = row_judgment.get("AI 판단 사유", "")
    return output


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="영업DB")
        worksheet = writer.sheets["영업DB"]
        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 45)
    return output.getvalue()


def render_sidebar() -> tuple[str, bool]:
    st.sidebar.header("연동 설정")
    sheet_url = st.sidebar.text_input(
        "영업금지 Google Sheet URL",
        placeholder="공개 CSV 또는 Google Sheet 공유 URL",
        help="실행 버튼을 눌렀을 때만 Google Sheet를 읽습니다.",
    )
    st.sidebar.header("AI 판단")
    use_ai_judgment = st.sidebar.checkbox(
        "AI 판단 사용",
        value=False,
        help="체크한 경우 최종 룰 기반 결과에 AI 판단 컬럼만 추가합니다.",
    )
    return sheet_url, use_ai_judgment


def render_forbidden_info(info: ForbiddenSheetInfo, encoding: str, row_count: int) -> None:
    if info.header_row is None:
        return
    summary = pd.DataFrame(
        [
            {"항목": "헤더 인식 행", "값": f"{info.header_row}행"},
            {"항목": "브랜드명 컬럼", "값": info.brand_column or "인식 안 됨"},
            {"항목": "사이트 컬럼", "값": info.url_column or "인식 안 됨"},
            {"항목": "연락처 컬럼", "값": info.contact_column or "인식 안 됨"},
            {"항목": "CSV 인코딩", "값": encoding or "확인 안 됨"},
            {"항목": "영업금지 대조 데이터", "값": f"{row_count}건"},
        ]
    )
    with st.expander("영업금지 리스트 인식 결과"):
        st.dataframe(summary, width="stretch", hide_index=True)


def render_quality_exclusions(stats: CollectionStats) -> None:
    if not stats.quality_excluded_rows:
        return
    preview = pd.DataFrame(stats.quality_excluded_rows).head(30)
    with st.expander("품질 필터 제외 사유 확인"):
        st.caption("테스트 및 검수용 미리보기입니다. 제외된 항목은 최종 결과와 Excel에 포함되지 않습니다.")
        st.dataframe(preview, width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📇", layout="wide")
    st.title(APP_TITLE)

    sheet_url, use_ai_judgment = render_sidebar()

    with st.form("collection_form"):
        col1, col2 = st.columns([2, 1])
        industry = col1.selectbox("업종 선택", INDUSTRY_OPTIONS, index=0)
        target_count = col2.number_input("수집 개수", min_value=1, max_value=50, value=10, step=1)
        submitted = st.form_submit_button("수집 시작", type="primary")

    st.caption("업종별 키워드 프리셋: " + " / ".join(KEYWORD_PRESETS[industry]))

    if not submitted:
        st.info("업종과 수집 개수를 선택한 뒤 수집 시작을 눌러주세요.")
        return

    try:
        with st.spinner("영업금지 리스트를 불러오는 중입니다."):
            forbidden, forbidden_info, encoding, sheet_warning = load_forbidden_sheet(sheet_url)
        render_forbidden_info(forbidden_info, encoding, len(forbidden))
        if sheet_warning:
            st.warning(sheet_warning)
    except Exception as exc:
        st.error(f"영업금지 리스트를 불러오지 못했습니다: {exc}")
        return

    try:
        with st.spinner("SerpAPI 검색 결과를 수집하는 중입니다."):
            candidates, stats = collect_brand_candidates(industry, int(target_count))
    except Exception as exc:
        st.error(str(exc))
        return

    if candidates.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("검색 결과 원본", stats.raw_count)
        col2.metric("품질 필터 제외", stats.quality_excluded_count)
        col3.metric("영업금지 제외", 0)
        col4.metric("최종 결과", 0)
        render_quality_exclusions(stats)
        st.warning("품질 필터링 후 남은 검색 결과가 없습니다.")
        return

    filtered, forbidden_excluded_count = apply_forbidden_filter(candidates, forbidden)
    if filtered.empty:
        final_df = pd.DataFrame(columns=["상태", "업종", "브랜드명", "사이트", "이메일", "전화번호", "수집출처", "수집일"])
    else:
        final_df = prepare_output_dataframe(filtered)

    if use_ai_judgment and not final_df.empty:
        try:
            with st.spinner("AI 판단을 추가하는 중입니다."):
                final_df = add_ai_judgment_columns(final_df)
        except Exception:
            st.warning("AI 판단을 완료하지 못해 기존 룰 기반 결과만 표시합니다.")

    usable_count = int((final_df["상태"] == "사용가능").sum()) if not final_df.empty else 0
    review_count = int((final_df["상태"] == "확인필요").sum()) if not final_df.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("검색 결과 원본", stats.raw_count)
    col2.metric("품질 필터 제외", stats.quality_excluded_count)
    col3.metric("영업금지 제외", forbidden_excluded_count)
    col4.metric("사용가능", usable_count)
    col5.metric("확인필요", review_count)
    render_quality_exclusions(stats)

    st.subheader("결과 미리보기")
    st.dataframe(final_df, width="stretch", hide_index=True)

    if final_df.empty:
        st.warning("최종 결과가 없습니다. 영업금지 리스트와 검색 조건을 확인해주세요.")
        return

    st.download_button(
        "Excel 다운로드",
        data=dataframe_to_excel_bytes(final_df),
        file_name=f"sales_db_{industry}_{current_collection_date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
