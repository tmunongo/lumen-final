import logging
from urllib.parse import urlparse

import httpx
import nh3
from bs4 import BeautifulSoup

from lumen.models import Artifact

logger = logging.getLogger(__name__)

REMOVE_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "object",
    "embed",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
}
ALLOWED_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "img",
    "figure",
    "figcaption",
    "br",
    "hr",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
}


def fetch_artifact_content(artifact_id: int) -> bool:
    try:
        artifact = Artifact.objects.get(id=artifact_id)
    except Artifact.DoesNotExist:
        return False

    if not artifact.source_url:
        return False

    headers = {"User-Agent": "Mozilla/5.0 (compatible; LumenSpace/1.0)"}
    try:
        response = httpx.get(
            artifact.source_url, headers=headers, follow_redirects=True, timeout=15.0
        )
        if response.status_code != 200:
            return False

        content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" in content_type or artifact.source_url.lower().endswith(
            ".pdf"
        ):
            return _handle_pdf(artifact)

        soup = BeautifulSoup(response.text, "html.parser")

        for tag_name in REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        title = _extract_title(soup) or artifact.source_url
        main_content_node = _extract_main_content(soup)

        raw_html = str(main_content_node) if main_content_node else ""
        cleaned_html = nh3.clean(
            raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES
        )

        artifact.title = title
        artifact.content = cleaned_html.strip()
        artifact.is_fetched = True
        artifact.artifact_type = "web_page"
        artifact.save()
        return True
    except Exception as exc:
        logger.error(f"fetch_artifact_content failed for artifact {artifact_id}: {exc}")
        return False


def _handle_pdf(artifact: Artifact) -> bool:
    try:
        parsed = urlparse(artifact.source_url)
        path = parsed.path
        filename = (
            path.split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ")
        )
        title = filename.title() if filename else "PDF Document"

        artifact.title = title
        artifact.artifact_type = "pdf"
        artifact.is_fetched = True
        artifact.save()
        return True
    except Exception as exc:
        logger.error(f"_handle_pdf failed for artifact {artifact.id}: {exc}")
        return False


def _extract_title(soup: BeautifulSoup) -> str:
    for sel in ["article h1", "h1", "title"]:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            return node.get_text(strip=True)
    return ""


def _extract_main_content(soup: BeautifulSoup):
    article = soup.find("article")
    if article:
        return article
    main = soup.find("main")
    if main:
        return main

    best_div, best_score = None, 0
    for div in soup.find_all("div"):
        p_count = len(div.find_all("p"))
        text_len = len(div.get_text())
        score = p_count * 3 + text_len / 100.0

        classes_and_id = f"{div.get('class', '')} {div.get('id', '')}".lower()
        if any(w in classes_and_id for w in ["comment", "footer", "nav", "sidebar"]):
            score -= 50
        if "article" in classes_and_id:
            score += 25
        if any(w in classes_and_id for w in ["main", "content"]):
            score += 20

        if score > best_score:
            best_score = score
            best_div = div

    return best_div or soup.body or soup
