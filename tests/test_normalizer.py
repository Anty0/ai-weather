"""Tests for the HTML normalizer strategies."""

from aiweather.visualization import HtmlNormalizer

normalizer = HtmlNormalizer()


def test_doctype_extraction():
    html = "chatter before\n<!DOCTYPE html><html><body>x</body></html>\nchatter after"
    assert normalizer.normalize(html) == "<!DOCTYPE html><html><body>x</body></html>"


def test_html_tag_extraction_without_doctype():
    html = "noise <html lang='en'><body>y</body></html> trailing"
    assert normalizer.normalize(html) == "<html lang='en'><body>y</body>"


def test_code_block_excludes_fences():
    html = "here you go:\n```html\n<h1>Hi</h1>\n```\nthanks"
    assert normalizer.normalize(html) == "<h1>Hi</h1>"


def test_code_block_inner_content_multiline():
    html = "```\n<div>\n<p>a</p>\n</div>\n```"
    assert normalizer.normalize(html) == "<div>\n<p>a</p>\n</div>"


def test_unterminated_fence_returns_raw_unchanged():
    html = "```html\nsome <b>content</b>\nmore text"
    result = normalizer.normalize(html)
    assert result == html


def test_incomplete_doctype_falls_through_to_raw():
    html = "intro <!DOCTYPE html><html><body>partial"
    assert normalizer.normalize(html) == html


def test_incomplete_html_tag_falls_through_to_raw():
    html = "preamble <html><body>still streaming"
    assert normalizer.normalize(html) == html


def test_noop_passthrough_plain_text():
    html = "just some text with no markers"
    assert normalizer.normalize(html) == html


def test_doctype_takes_precedence_over_code_block():
    html = "```html\n<!DOCTYPE html><html>z</html>\n```"
    assert normalizer.normalize(html) == "<!DOCTYPE html><html>z</html>"
