from __future__ import annotations

import json
import random
import re
import time
import html
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from config import get_taobao_cookie


DEFAULT_HEADERS = {
    "Accept": "application/json,text/javascript,*/*;q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}


class TaobaoCollectionError(RuntimeError):
    pass


@dataclass
class ParsedProduct:
    platform: str
    item_id: str
    seller_id: str | None
    title: str
    canonical_url: str


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _decode_escaped_text(text: str) -> str:
    value = str(text or "")
    try:
        value = json.loads(f'"{value}"')
    except Exception:
        try:
            value = value.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass
    return html.unescape(_clean_text(value))


def _parse_jsonp(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return {}
    if raw.startswith("{") or raw.startswith("["):
        return json.loads(raw)
    start = raw.find("(")
    end = raw.rfind(")")
    if start >= 0 and end > start:
        return json.loads(raw[start + 1 : end])
    return json.loads(raw)


def _extract_item_id(product_url: str) -> str:
    parsed = urlparse(product_url)
    qs = parse_qs(parsed.query)
    for key in ("id", "item_id", "itemId"):
        values = qs.get(key)
        if values and values[0].strip():
            return values[0].strip()

    m = re.search(r"/item(?:-|_)?(\d+)", parsed.path)
    if m:
        return m.group(1)
    raise TaobaoCollectionError("无法从商品链接中解析 item_id，请确认链接包含 id 参数。")


def _extract_title(html: str) -> str:
    generic_titles = {
        "商品详情",
        "宝贝描述",
        "卖家服务",
        "物流服务",
        "用户评价",
        "图文详情",
    }
    patterns = [
        r'class="mainTitle[^"]*"\s+title="([^"]+)"',
        r'class="mainTitle[^"]*">([^<]+)<',
        r'class="MainTitle[^"]*"\s*><span[^>]*title="([^"]+)"',
        r'<meta\s+property="og:title"\s+content="([^"]+)"',
        r'<meta\s+name="keywords"\s+content="([^"]+)"',
        r"<title>(.*?)</title>",
        r'"title"\s*:\s*"([^"]+)"',
        r'"itemTitle"\s*:\s*"([^"]+)"',
    ]
    candidates: list[str] = []
    for pattern in patterns:
        for m in re.finditer(pattern, html, flags=re.IGNORECASE | re.DOTALL):
            title = _decode_escaped_text(m.group(1)).replace("_淘宝搜索", "")
            if title:
                candidates.append(title)
    if not candidates:
        return ""

    ranked = sorted(
        {title for title in candidates if title},
        key=lambda title: (
            0 if title in generic_titles else 1,
            1 if len(title) >= 8 else 0,
            len(title),
        ),
        reverse=True,
    )
    for title in ranked:
        if title not in generic_titles and len(title) >= 8:
            return title
    for title in ranked:
        if title not in generic_titles:
            return title
    return ranked[0] if ranked else ""


def _extract_user_nick(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("nick", "displayUserNick", "userNick", "user"):
            text = _clean_text(value.get(key))
            if text:
                return text
        return ""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text.replace("'", '"'))
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return _extract_user_nick(parsed)
        return _clean_text(text)
    return ""


def _extract_seller_id(html: str) -> str | None:
    patterns = [
        r'"sellerId"\s*:\s*"?(?P<id>\d+)"?',
        r'"userId"\s*:\s*"?(?P<id>\d+)"?',
        r'"seller_id"\s*:\s*"?(?P<id>\d+)"?',
        r'"shopId"\s*:\s*"?(?P<id>\d+)"?',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, flags=re.IGNORECASE)
        if m:
            return m.group("id")
    return None


def _fetch_product_html(session: requests.Session, product_url: str, cookie: str, timeout: float) -> ParsedProduct:
    item_id = _extract_item_id(product_url)
    platform = "tmall" if "tmall.com" in product_url else "taobao"
    headers = dict(DEFAULT_HEADERS)
    headers["Referer"] = product_url
    if cookie.strip():
        headers["Cookie"] = cookie.strip()
    response = session.get(product_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    html = response.text
    title = _extract_title(html) or f"{platform}-{item_id}"
    seller_id = _extract_seller_id(html)
    return ParsedProduct(
        platform=platform,
        item_id=item_id,
        seller_id=seller_id,
        title=title,
        canonical_url=product_url,
    )


def _tmall_endpoint(item_id: str, seller_id: str, page: int, page_size: int) -> str:
    stamp = int(time.time() * 1000)
    callback = f"jsonp{stamp}{random.randint(10, 99)}"
    return (
        "https://rate.tmall.com/list_detail_rate.htm"
        f"?itemId={item_id}&sellerId={seller_id}&order=3&currentPage={page}"
        f"&pageSize={page_size}&append=0&content=1&tagId=&posi=&picture=&groupId=&ua=098%23E1hvvpvUvbpviyCkvvvvvjiPR2dCgj3bR2PZ6jEPPmPmAjYPR2dCgj3bR2dE6jiRjphvCvvvMMCKE7Qm5eCvmn7thvm5vpvhvC9AP5vpvhvC9APyvH2QhvCpvvv9Cvpv9vvCvp8%2B9phv2I2oIiY2o8dC6AqzgD84HNQwx68mr2R4eXjU8qD7rQwcA9XE7eQj7muHzKD%3D%3D"
        f"&needFold=0&_ksTS={stamp}_100&callback={callback}"
    )


def _taobao_endpoint(item_id: str, page: int, page_size: int) -> str:
    callback = f"jsonp_tb_{int(time.time() * 1000)}"
    return (
        "https://rate.taobao.com/feedRateList.htm"
        f"?auctionNumId={item_id}&currentPageNum={page}&pageSize={page_size}"
        f"&rateType=&orderType=sort_weight&expression=&rateContent=&append=0"
        f"&callback={callback}"
    )


def _normalize_tmall_review(item: dict[str, Any], index: int, product: ParsedProduct) -> dict[str, Any]:
    return {
        "review_id": str(item.get("rateId") or item.get("id") or f"{product.item_id}-{index}"),
        "review_text": _clean_text(item.get("rateContent") or item.get("content") or ""),
        "review_time": _clean_text(item.get("rateDate") or item.get("date") or ""),
        "rating": item.get("auctionSku") or item.get("tamllSweetLevel") or item.get("grade"),
        "product_name": product.title,
        "shop_name": _extract_user_nick(item.get("displayUserNick") or item.get("userNick") or item.get("user")),
        "source_platform": product.platform,
        "product_url": product.canonical_url,
    }


def _normalize_taobao_review(item: dict[str, Any], index: int, product: ParsedProduct) -> dict[str, Any]:
    return {
        "review_id": str(item.get("id") or item.get("rateId") or f"{product.item_id}-{index}"),
        "review_text": _clean_text(item.get("content") or item.get("rateContent") or ""),
        "review_time": _clean_text(item.get("date") or item.get("rateDate") or ""),
        "rating": item.get("rate") or item.get("score"),
        "product_name": product.title,
        "shop_name": _extract_user_nick(item.get("user") or item.get("userNick") or item.get("displayUserNick")),
        "source_platform": product.platform,
        "product_url": product.canonical_url,
    }


def _extract_tmall_reviews(payload: dict[str, Any], product: ParsedProduct) -> list[dict[str, Any]]:
    candidates = [
        payload.get("rateDetail", {}).get("rateList", []),
        payload.get("rateList", []),
        payload.get("module", {}).get("rateList", []),
    ]
    for rows in candidates:
        if isinstance(rows, list) and rows:
            return [
                row
                for idx, item in enumerate(rows, start=1)
                if (row := _normalize_tmall_review(item, idx, product)).get("review_text")
            ]
    return []


def _extract_taobao_reviews(payload: dict[str, Any], product: ParsedProduct) -> list[dict[str, Any]]:
    candidates = [
        payload.get("comments", []),
        payload.get("comment", {}).get("comments", []),
        payload.get("rateDetail", {}).get("rateList", []),
        payload.get("rateList", []),
    ]
    for rows in candidates:
        if isinstance(rows, list) and rows:
            return [
                row
                for idx, item in enumerate(rows, start=1)
                if (row := _normalize_taobao_review(item, idx, product)).get("review_text")
            ]
    return []


def collect_taobao_reviews(
    *,
    product_url: str,
    cookie: str,
    pages: int = 1,
    page_size: int = 20,
    seller_id_override: str | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    if not (product_url or "").strip():
        raise TaobaoCollectionError("商品链接不能为空。")
    cookie = (cookie or "").strip() or get_taobao_cookie()
    if not (cookie or "").strip():
        raise TaobaoCollectionError("需要提供登录后的 Cookie 才能在 Streamlit Cloud 中尝试采集。")

    session = requests.Session()
    session.trust_env = False
    product = _fetch_product_html(session, product_url.strip(), cookie, timeout)
    if seller_id_override:
        product = ParsedProduct(
            platform=product.platform,
            item_id=product.item_id,
            seller_id=seller_id_override.strip(),
            title=product.title,
            canonical_url=product.canonical_url,
        )

    headers = dict(DEFAULT_HEADERS)
    headers["Referer"] = product.canonical_url
    headers["Cookie"] = cookie.strip()

    reviews: list[dict[str, Any]] = []
    errors: list[str] = []

    for page in range(1, max(1, int(pages)) + 1):
        try:
            if product.platform == "tmall":
                if not product.seller_id:
                    raise TaobaoCollectionError("未能从页面解析 seller_id，请手动填写 seller_id 后重试。")
                url = _tmall_endpoint(product.item_id, product.seller_id, page, page_size)
                response = session.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                payload = _parse_jsonp(response.text)
                page_reviews = _extract_tmall_reviews(payload, product)
            else:
                url = _taobao_endpoint(product.item_id, page, page_size)
                response = session.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                payload = _parse_jsonp(response.text)
                page_reviews = _extract_taobao_reviews(payload, product)

            if not page_reviews:
                errors.append(f"page {page}: empty or blocked response")
                break
            reviews.extend(page_reviews)
        except Exception as exc:
            errors.append(f"page {page}: {type(exc).__name__}: {exc}")
            break

    if not reviews:
        hint = (
            "采集失败。请确认商品链接有效、Cookie 仍然可用，并尽量在刚登录后重试。"
            " 如果是天猫商品，也可以手动补充 seller_id。"
        )
        if errors:
            hint = f"{hint} 详情: {'; '.join(errors[:2])}"
        raise TaobaoCollectionError(hint)

    return {
        "platform": product.platform,
        "item_id": product.item_id,
        "seller_id": product.seller_id or "",
        "product_name": product.title,
        "product_url": product.canonical_url,
        "pages_requested": max(1, int(pages)),
        "page_size": max(1, int(page_size)),
        "review_count": len(reviews),
        "reviews": reviews,
        "warnings": errors,
    }
