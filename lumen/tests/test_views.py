import pytest

from lumen.models import Artifact, ArtifactHighlight, ArtifactLink, Project


@pytest.mark.django_db
class TestProjectViews:
    def test_project_crud_and_archiving(self, client):
        client.session["authenticated"] = True
        session = client.session
        session["authenticated"] = True
        session.save()

        # Create Project
        resp = client.post("/projects/create/", {"name": "Deep Research"})
        assert resp.status_code == 302
        project = Project.objects.get(name="Deep Research")

        # Project Detail
        detail_resp = client.get(f"/projects/{project.id}/")
        assert detail_resp.status_code == 200

        # Archive Project
        archive_resp = client.post(f"/projects/{project.id}/archive/")
        assert archive_resp.status_code == 302
        project.refresh_from_db()
        assert project.is_archived

        # Unarchive Project
        unarchive_resp = client.post(f"/projects/{project.id}/unarchive/")
        assert unarchive_resp.status_code == 302
        project.refresh_from_db()
        assert not project.is_archived

    def test_project_export(self, client):
        client.session["authenticated"] = True
        session = client.session
        session["authenticated"] = True
        session.save()

        project = Project.objects.create(name="Export Workspace")
        Artifact.objects.create(
            project=project, title="Note 1", artifact_type="note", content="Hello World"
        )

        # Export Markdown
        exp_md = client.get(f"/projects/{project.id}/export/?format=markdown")
        assert exp_md.status_code == 200
        assert "text/markdown" in exp_md["Content-Type"]
        assert "Note 1" in exp_md.content.decode()

        # Export JSON
        exp_json = client.get(f"/projects/{project.id}/export/?format=json")
        assert exp_json.status_code == 200
        assert "application/json" in exp_json["Content-Type"]


@pytest.mark.django_db
class TestArtifactViews:
    def test_artifact_creation_and_tagging(self, client):
        session = client.session
        session["authenticated"] = True
        session.save()

        project = Project.objects.create(name="Artifact Workspace")

        # Create Note
        create_resp = client.post(
            f"/projects/{project.id}/artifacts/create/",
            {
                "title": "Quantum Computing",
                "artifact_type": "note",
                "content": "Superposition and Entanglement.",
            },
        )
        assert create_resp.status_code == 302
        artifact = Artifact.objects.get(title="Quantum Computing")

        # Add Tag
        tag_add_resp = client.post(
            f"/projects/{project.id}/artifacts/{artifact.id}/add_tag/",
            {"tag_name": "physics"},
        )
        assert tag_add_resp.status_code in [200, 302]
        assert "physics" in artifact.tag_names

        # Remove Tag
        tag_rem_resp = client.post(
            f"/projects/{project.id}/artifacts/{artifact.id}/remove_tag/",
            {"tag_name": "physics"},
        )
        assert tag_rem_resp.status_code in [200, 302]
        assert "physics" not in artifact.tag_names


@pytest.mark.django_db
class TestHighlightAndLinkViews:
    def test_create_highlight_and_link(self, client):
        session = client.session
        session["authenticated"] = True
        session.save()

        project = Project.objects.create(name="Graph Workspace")
        art1 = Artifact.objects.create(
            project=project, title="Paper A", artifact_type="note"
        )
        art2 = Artifact.objects.create(
            project=project, title="Paper B", artifact_type="note"
        )

        # Create Highlight
        hl_resp = client.post(
            f"/projects/{project.id}/artifacts/{art1.id}/highlights/create/",
            {"selected_text": "Key discovery", "style": "green"},
        )
        assert hl_resp.status_code in [200, 302]
        assert ArtifactHighlight.objects.filter(
            artifact=art1, selected_text="Key discovery"
        ).exists()

        # Create Link
        link_resp = client.post(
            "/artifact_links/create/",
            {
                "project_id": project.id,
                "source_artifact_id": art1.id,
                "target_artifact_id": art2.id,
                "link_type": "supports",
            },
        )
        assert link_resp.status_code in [200, 302]
        assert ArtifactLink.objects.filter(
            source_artifact=art1, target_artifact=art2
        ).exists()


@pytest.mark.django_db
class TestRelationshipsView:
    def test_relationships_index(self, client):
        session = client.session
        session["authenticated"] = True
        session.save()

        project = Project.objects.create(name="Rel Workspace")
        art1 = Artifact.objects.create(
            project=project, title="A1", artifact_type="note"
        )
        art2 = Artifact.objects.create(
            project=project, title="A2", artifact_type="note"
        )
        art1.add_tag("ai")
        art2.add_tag("ai")

        resp = client.get(
            f"/projects/{project.id}/relationships/?artifact_id={art1.id}"
        )
        assert resp.status_code == 200
