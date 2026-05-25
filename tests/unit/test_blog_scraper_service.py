import pytest
from fastapi import HTTPException

from app.services.blog_scraper_service import (
    _parse_blog_html,
    _validate_public_http_url,
)


def test_blog_url_validator_rejects_non_http_urls():
    with pytest.raises(HTTPException) as exc_info:
        _validate_public_http_url("file:///etc/passwd")

    assert exc_info.value.status_code == 422


def test_blog_url_validator_rejects_localhost():
    with pytest.raises(HTTPException) as exc_info:
        _validate_public_http_url("http://localhost:3000/article")

    assert exc_info.value.status_code == 400


def test_blog_html_parser_extracts_title_canonical_text_and_metadata():
    html = """
    <html>
      <head>
        <title>Example Article</title>
        <link rel="canonical" href="/canonical-article" />
        <meta name="description" content="A useful article" />
        <meta name="author" content="Jane Doe" />
      </head>
      <body>
        <article>
          <h1>Example Article</h1>
          <p>This paragraph contains enough readable text for the parser to accept it.</p>
          <p>This second paragraph adds more article body content for indexing.</p>
        </article>
      </body>
    </html>
    """

    result = _parse_blog_html(html, "https://example.com/source")

    assert result["title"] == "Example Article"
    assert result["url"] == "https://example.com/canonical-article"
    assert "second paragraph" in result["text"]
    assert result["metadata"] == {
        "description": "A useful article",
        "author": "Jane Doe",
    }
