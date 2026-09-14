from django.urls import path

from lumen import views

urlpatterns = [
    path("", views.projects_index, name="projects_index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Projects
    path("projects/create/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/archive/", views.project_archive, name="project_archive"),
    path(
        "projects/<int:pk>/unarchive/",
        views.project_unarchive,
        name="project_unarchive",
    ),
    path("projects/<int:pk>/export/", views.project_export, name="project_export"),
    # Artifacts
    path(
        "projects/<int:project_id>/artifacts/create/",
        views.artifact_create,
        name="artifact_create",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:pk>/delete/",
        views.artifact_delete,
        name="artifact_delete",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:pk>/fetch_content/",
        views.artifact_fetch_content,
        name="artifact_fetch_content",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:pk>/add_tag/",
        views.artifact_add_tag,
        name="artifact_add_tag",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:pk>/remove_tag/",
        views.artifact_remove_tag,
        name="artifact_remove_tag",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:pk>/proxy_pdf/",
        views.proxy_pdf,
        name="proxy_pdf",
    ),
    # Highlights & Links
    path(
        "projects/<int:project_id>/artifacts/<int:artifact_id>/highlights/create/",
        views.highlight_create,
        name="highlight_create",
    ),
    path(
        "projects/<int:project_id>/artifacts/<int:artifact_id>/highlights/<int:pk>/delete/",
        views.highlight_delete,
        name="highlight_delete",
    ),
    path("artifact_links/create/", views.link_create, name="link_create"),
    path(
        "artifact_links/<int:pk>/delete/",
        views.link_delete,
        name="link_delete",
    ),
    # Relationships
    path(
        "projects/<int:project_id>/relationships/",
        views.relationships_index,
        name="relationships_index",
    ),
]
