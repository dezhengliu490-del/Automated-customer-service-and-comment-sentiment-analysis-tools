from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import get_amazon_cookie, normalize_cookie_string


DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}

_ASIN_RE = re.compile(r"\b([A-Z0-9]{10})\b", re.IGNORECASE)


class AmazonCollectionError(RuntimeError):
    pass


@dataclass
class ParsedAmazonProduct:
    asin: str
    domain: str
    title: str
    canonical_url: str
    review_url: str


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _extract_asin(product_url: str) -> str:
    raw = product_url.strip()
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product-reviews/([A-Z0-9]{10})",
        r"/reviews/([A-Z0-9]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()

    parsed = urlparse(raw)
    for candidate in re.split(r"[^A-Za-z0-9]+", parsed.path):
        if _ASIN_RE.fullmatch(candidate or ""):
            return candidate.upper()
    raise AmazonCollectionError("无法从 Amazon 链接中解析 ASIN，请确认链接包含 /dp/ASIN 或 /product-reviews/ASIN。")


def _extract_domain(product_url: str) -> str:
    host = urlparse(product_url.strip()).netloc.lower()
    if not host:
        return "www.amazon.com"
    if host.startswith("smile."):
        host = "www." + host.split(".", 1)[1]
    return host


def _detect_captcha(text: str) -> bool:
    lowered = (text or "").lower()
    return "enter the characters you see below" in lowered or "type the characters you see in this image" in lowered


def _extract_title(soup: BeautifulSoup, asin: str) -> str:
    selectors = [
        "#cm_cr-product_info a[data-hook='product-link']",
        "a[data-hook='product-link']",
        "span[data-hook='product-link']",
        "#productTitle",
        "title",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        text = _clean_text(node.get_text(" ", strip=True) if node else "")
        if text and text.upper() != asin:
            return text.replace(": Amazon.com", "").replace("Amazon.com: ", "")
    return f"amazon-{asin}"


def _parse_date(text: str) -> str:
    raw = _clean_text(text)
    if " on " in raw:
        raw = raw.split(" on ", 1)[-1]
    for fmt in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _extract_reviews(html: str, product: ParsedAmazonProduct) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for idx, box in enumerate(soup.select("[data-hook='review']"), start=1):
        review_id = box.get("id") or f"{product.asin}-{idx}"
        reviewer_name = _clean_text((box.select_one(".a-profile-name") or {}).get_text(" ", strip=True) if box.select_one(".a-profile-name") else "")

        rating_node = box.select_one("[data-hook='review-star-rating'], [data-hook='cmps-review-star-rating']")
        rating_text = _clean_text(rating_node.get_text(" ", strip=True) if rating_node else "")
        rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
        rating = rating_match.group(1) if rating_match else ""

        title_node = box.select_one("[data-hook='review-title']")
        review_title = _clean_text(title_node.get_text(" ", strip=True) if title_node else "")

        date_node = box.select_one("[data-hook='review-date']")
        review_time = _parse_date(date_node.get_text(" ", strip=True) if date_node else "")

        body_node = box.select_one("[data-hook='review-body']")
        review_text = _clean_text(body_node.get_text(" ", strip=True) if body_node else "")
        if not review_text:
            continue

        rows.append(
            {
                "review_id": review_id,
                "review_text": review_text,
                "review_time": review_time,
                "rating": rating,
                "product_name": product.title,
                "shop_name": "",
                "reviewer_name": reviewer_name,
                "review_title": review_title,
                "source_platform": f"amazon:{product.domain}",
                "product_url": product.canonical_url,
            }
        )
    return rows


def _prepare_product(session: requests.Session, product_url: str, timeout: float) -> ParsedAmazonProduct:
    asin = _extract_asin(product_url)
    domain = _extract_domain(product_url)
    canonical_url = f"https://{domain}/dp/{asin}"
    response = session.get(canonical_url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if _detect_captcha(response.text):
        raise AmazonCollectionError("Amazon 返回了验证码页面，当前请求被风控拦截，请稍后重试或减少抓取频率。")
    soup = BeautifulSoup(response.text, "html.parser")
    title = _extract_title(soup, asin)
    review_url = f"https://{domain}/product-reviews/{asin}/"
    return ParsedAmazonProduct(
        asin=asin,
        domain=domain,
        title=title,
        canonical_url=canonical_url,
        review_url=review_url,
    )


def collect_amazon_reviews(
    *,
    product_url: str,
    cookie: str = "",
    pages: int = 1,
    timeout: float = 20.0,
) -> dict[str, Any]:
    if not (product_url or "").strip():
        raise AmazonCollectionError("Amazon 商品链接不能为空。")

    cookie = normalize_cookie_string(cookie) or get_amazon_cookie()

    session = requests.Session()
    session.trust_env = False
    if cookie:
        session.headers.update({"Cookie": cookie})
    product = _prepare_product(session, product_url.strip(), timeout)

    reviews: list[dict[str, Any]] = []
    warnings: list[str] = []
    page_count = max(1, int(pages))

    for page in range(1, page_count + 1):
        params = {
            "ie": "UTF8",
            "reviewerType": "all_reviews",
            "pageNumber": page,
            "sortBy": "recent",
        }
        try:
            response = session.get(product.review_url, headers=DEFAULT_HEADERS, params=params, timeout=timeout)
            response.raise_for_status()
            if _detect_captcha(response.text):
                warnings.append(f"page {page}: Amazon returned captcha/blocked page")
                break
            page_reviews = _extract_reviews(response.text, product)
            if not page_reviews:
                warnings.append(f"page {page}: empty or blocked response")
                break
            reviews.extend(page_reviews)
        except requests.HTTPError as exc:
            warnings.append(f"page {page}: HTTPError: {exc}")
            break
        except AmazonCollectionError:
            raise
        except Exception as exc:
            warnings.append(f"page {page}: {type(exc).__name__}: {exc}")
            break

    if not reviews:
        hint = "采集失败。请确认 Amazon 商品链接有效，并尽量减少页数后重试。"
        if warnings:
            hint = f"{hint} 详情: {'; '.join(warnings[:2])}"
        raise AmazonCollectionError(hint)

    return {
        "platform": "amazon",
        "item_id": product.asin,
        "seller_id": "",
        "product_name": product.title,
        "product_url": product.canonical_url,
        "pages_requested": page_count,
        "page_size": 10,
        "review_count": len(reviews),
        "reviews": reviews,
        "warnings": warnings,
        "marketplace": product.domain,
    }
