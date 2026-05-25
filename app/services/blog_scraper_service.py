import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException, status


BLOCKED_HOSTNAMES = {"localhost"}
READABLE_TEXT_TAGS = {
    "article",
    "main",
    "section",
    "p",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "blockquote"
}
SKIPPED_TAGS = {"script", "style", "noscript", "svg", "canvas"}


class ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.metadata: dict[str, str] = {}
        self.canonical_url: str | None = None
        self._tag_stack: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = {key.lower(): value for key, value in attrs if value}
        self._tag_stack.append(tag)

        if tag in SKIPPED_TAGS:
            self._skip_depth += 1

        if tag == "link" and "canonical" in attrs_dict.get("rel", "").split():
            self.canonical_url = attrs_dict.get("href")

        if tag == "meta":
            name = attrs_dict.get("name") or attrs_dict.get("property")
            content = attrs_dict.get("content")

            if not name or not content:
                return

            metadata_keys = {
                "description": "description",
                "og:description": "description",
                "author": "author",
                "article:author": "author",
                "article:published_time": "published_date",
                "date": "published_date"
            }

            mapped_name = metadata_keys.get(name.lower())

            if mapped_name and mapped_name not in self.metadata:
                self.metadata[mapped_name] = content.strip()

    def handle_endtag(self, tag: str):
        if tag in SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str):
        if self._skip_depth:
            return

        text = re.sub(r"\s+", " ", data).strip()

        if not text:
            return

        current_tag = self._tag_stack[-1] if self._tag_stack else ""

        if current_tag == "title":
            self.title_parts.append(text)

        if current_tag in READABLE_TEXT_TAGS:
            self.text_parts.append(text)


def _validate_public_http_url(url: str) -> None:
    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only HTTP and HTTPS URLs are allowed"
        )

    if not parsed_url.hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL host is required"
        )

    hostname = parsed_url.hostname.lower()

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Localhost URLs are not allowed"
        )

    try:
        ip_address = ipaddress.ip_address(hostname)
        _validate_public_ip(ip_address)
        return
    except ValueError:
        pass

    try:
        address_infos = socket.getaddrinfo(hostname, parsed_url.port or 443)
    except socket.gaierror as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not resolve URL host: {str(exception)}"
        )

    for address_info in address_infos:
        ip_value = address_info[4][0]
        _validate_public_ip(ipaddress.ip_address(ip_value))


def _validate_public_ip(ip_address: ipaddress._BaseAddress) -> None:
    if (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_reserved
        or ip_address.is_unspecified
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internal or private URLs are not allowed"
        )


def _parse_blog_html(html: str, fallback_url: str) -> dict:
    parser = ReadableHTMLParser()
    parser.feed(html)

    title = " ".join(parser.title_parts).strip() or fallback_url
    text = "\n\n".join(parser.text_parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract enough readable blog content"
        )

    return {
        "url": urljoin(fallback_url, parser.canonical_url) if parser.canonical_url else fallback_url,
        "title": title,
        "text": text,
        "metadata": parser.metadata,
        "scraper": "httpx-html"
    }


async def scrape_blog_page(url: str) -> dict:
    _validate_public_http_url(url)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            headers={"User-Agent": "kb-pdf-backend/1.0"}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

    except httpx.HTTPStatusError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Blog URL returned HTTP {exception.response.status_code}"
        )

    except httpx.RequestError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch blog URL: {str(exception)}"
        )

    final_url = str(response.url)
    _validate_public_http_url(final_url)

    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blog URL did not return an HTML page"
        )

    scraped = _parse_blog_html(response.text, final_url)

    return {
        **scraped,
        "url": scraped["url"] or final_url
    }

