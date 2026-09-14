import pytest
from django.core.exceptions import ValidationError

from lumen.models import Artifact, ArtifactHighlight, ArtifactLink, Project


@pytest.mark.django_db
class TestProjectModel:
    def test_create_project(self):
        project = Project.objects.create(name=" Research Project ")
        assert project.name == "Research Project"
        assert not project.is_archived
        assert project.artifact_count == 0

    def test_archive_and_unarchive(self):
        project = Project.objects.create(name="AI Notes")
        project.archive()
        assert project.is_archived
        assert project in Project.objects.archived()
        assert project not in Project.objects.active()

        project.unarchive()
        assert not project.is_archived
        assert project in Project.objects.active()

    def test_duplicate_name_validation(self):
        Project.objects.create(name="Unique Project")
        with pytest.raises(ValidationError):
            p2 = Project(name="unique project")
            p2.full_clean()


@pytest.mark.django_db
class TestArtifactModel:
    def test_create_artifact_and_tags(self):
        project = Project.objects.create(name="Project A")
        artifact = Artifact.objects.create(
            project=project,
            title="Sample Note",
            artifact_type="note",
            content="This is a simple test note content with multiple words.",
        )
        assert artifact.type_icon == "📝"
        assert artifact.reading_time_minutes == 1

        artifact.add_tag(" Python ")
        artifact.add_tag("django")
        assert set(artifact.tag_names) == {"python", "django"}

        artifact.remove_tag("python")
        assert artifact.tag_names == ["django"]

        artifact.set_tags(["web", "research", "django"])
        assert set(artifact.tag_names) == {"web", "research", "django"}

    def test_artifact_validations(self):
        project = Project.objects.create(name="Project B")
        # Quote requires attribution
        quote = Artifact(
            project=project, title="A Quote", artifact_type="quote", content="Hello"
        )
        with pytest.raises(ValidationError):
            quote.full_clean()

        # Web page requires source_url
        web = Artifact(project=project, title="Web Article", artifact_type="web_page")
        with pytest.raises(ValidationError):
            web.full_clean()


@pytest.mark.django_db
class TestArtifactHighlightModel:
    def test_highlight_color_class(self):
        project = Project.objects.create(name="Project C")
        artifact = Artifact.objects.create(
            project=project, title="Note", artifact_type="note"
        )
        highlight = ArtifactHighlight.objects.create(
            artifact=artifact, selected_text="important text", style="green"
        )
        assert highlight.color_class == "highlight--green"


@pytest.mark.django_db
class TestArtifactLinkModel:
    def test_link_creation_and_self_link_prevention(self):
        project = Project.objects.create(name="Project D")
        art1 = Artifact.objects.create(
            project=project, title="Art 1", artifact_type="note"
        )
        art2 = Artifact.objects.create(
            project=project, title="Art 2", artifact_type="note"
        )

        link = ArtifactLink.objects.create(
            project=project,
            source_artifact=art1,
            target_artifact=art2,
            link_type="supports",
        )
        assert link.type_label == "Supports"

        # Prevent self link
        self_link = ArtifactLink(
            project=project,
            source_artifact=art1,
            target_artifact=art1,
            link_type="related",
        )
        with pytest.raises(ValidationError):
            self_link.full_clean()
