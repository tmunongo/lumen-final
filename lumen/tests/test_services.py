import json

import pytest

from lumen.models import Artifact, Project
from lumen.services.exporter import BibliographyExporter
from lumen.services.web_fetcher import fetch_artifact_content


@pytest.mark.django_db
class TestBibliographyExporter:
    def test_export_formats(self):
        project = Project.objects.create(name="Exporter Test")
        art1 = Artifact.objects.create(
            project=project,
            title="Django Docs",
            artifact_type="web_page",
            source_url="https://docs.djangoproject.com",
            content="Official Django Documentation",
        )
        art1.add_tag("python")
        art1.add_tag("django")

        art2 = Artifact.objects.create(
            project=project,
            title="Important Quote",
            artifact_type="quote",
            attribution="Guido van Rossum",
            content="Readability counts.",
        )

        artifacts = [art1, art2]

        # Markdown Export
        md = BibliographyExporter.export_markdown(artifacts)
        assert "# Bibliography" in md
        assert "Django Docs" in md
        assert "Readability counts." in md

        # CSV Export
        csv_out = BibliographyExporter.export_csv(artifacts)
        assert "Title,URL,Type,Created At,Tags" in csv_out
        assert "Django Docs" in csv_out

        # JSON Export
        json_out = BibliographyExporter.export_json(artifacts)
        parsed = json.loads(json_out)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Django Docs"
        assert set(parsed[0]["tags"]) == {"python", "django"}

        # BibTeX Export
        bib = BibliographyExporter.export_bibtex(artifacts)
        assert "@misc{" in bib
        assert "Django Docs" in bib


@pytest.mark.django_db
class TestWebFetcher:
    def test_fetch_html_artifact(self, httpx_mock):
        project = Project.objects.create(name="Fetcher Test")
        art = Artifact.objects.create(
            project=project,
            title="http://example.com/article",
            artifact_type="raw_link",
            source_url="http://example.com/article",
        )

        html_content = """
        <html>
            <head><title>Awesome Python Guide</title></head>
            <body>
                <script>alert("ignore me");</script>
                <article>
                    <h1>Awesome Python Guide</h1>
                    <p>Python is a great programming language.</p>
                </article>
            </body>
        </html>
        """
        httpx_mock.add_response(url="http://example.com/article", text=html_content)

        success = fetch_artifact_content(art.id)
        assert success
        art.refresh_from_db()

        assert art.title == "Awesome Python Guide"
        assert art.is_fetched
        assert art.artifact_type == "web_page"
        assert "Python is a great programming language" in art.content
        assert "<script>" not in art.content

    def test_fetch_pdf_artifact(self, httpx_mock):
        project = Project.objects.create(name="PDF Test")
        art = Artifact.objects.create(
            project=project,
            title="http://example.com/paper.pdf",
            artifact_type="raw_link",
            source_url="http://example.com/paper.pdf",
        )

        httpx_mock.add_response(
            url="http://example.com/paper.pdf",
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4 sample content",
        )

        success = fetch_artifact_content(art.id)
        assert success
        art.refresh_from_db()

        assert art.is_fetched
        assert art.artifact_type == "pdf"
        assert "Paper" in art.title
