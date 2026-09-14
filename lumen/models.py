import math
import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import strip_tags


class ProjectQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_archived=False)

    def archived(self):
        return self.filter(is_archived=True)

    def by_name(self):
        return self.order_by("name")

    def by_modified(self):
        return self.order_by("-updated_at")

    def by_created(self):
        return self.order_by("-created_at")


class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.name:
            self.name = self.name.strip()
            query = Project.objects.filter(name__iexact=self.name)
            if self.pk:
                query = query.exclude(pk=self.pk)
            if query.exists():
                raise ValidationError({"name": "Project name already exists."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def archive(self):
        self.is_archived = True
        self.save()

    def unarchive(self):
        self.is_archived = False
        self.save()

    @property
    def artifact_count(self):
        return self.artifacts.count()


class ArtifactQuerySet(models.QuerySet):
    def by_project(self, project_id):
        return self.filter(project_id=project_id)

    def by_type(self, artifact_type):
        return self.filter(artifact_type=artifact_type)

    def fetched(self):
        return self.filter(is_fetched=True)

    def by_tag(self, tag_name):
        return self.filter(artifact_tags__name=tag_name.strip().lower())

    def recent(self):
        return self.order_by("-created_at")


class Artifact(models.Model):
    TYPES = [
        ("web_page", "Web Page"),
        ("raw_link", "Raw Link"),
        ("note", "Note"),
        ("quote", "Quote"),
        ("image", "Image"),
        ("markdown", "Markdown"),
        ("pdf", "PDF"),
    ]

    LINK_TYPES = [
        ("related", "Related"),
        ("supports", "Supports"),
        ("contradicts", "Contradicts"),
        ("background", "Background"),
        ("quotes", "Quotes"),
        ("depends_on", "Depends on"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="artifacts"
    )
    title = models.CharField(max_length=500)
    artifact_type = models.CharField(max_length=50, choices=TYPES)
    content = models.TextField(blank=True, null=True)
    source_url = models.URLField(max_length=2000, blank=True, null=True)
    attribution = models.CharField(max_length=500, blank=True, null=True)
    local_asset_path = models.CharField(max_length=500, blank=True, null=True)
    is_fetched = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArtifactQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.artifact_type})"

    def clean(self):
        if self.artifact_type == "quote" and not self.attribution:
            raise ValidationError(
                {"attribution": "Attribution is required for quote artifacts."}
            )
        if (
            self.artifact_type in ["web_page", "raw_link", "pdf"]
            and not self.source_url
        ):
            raise ValidationError(
                {"source_url": "Source URL is required for this artifact type."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.local_asset_path and os.path.exists(self.local_asset_path):
            try:
                os.remove(self.local_asset_path)
            except OSError:
                pass
        super().delete(*args, **kwargs)

    @property
    def tag_names(self):
        return list(self.artifact_tags.values_list("name", flat=True))

    def add_tag(self, name):
        normalized = name.strip().lower()
        if not normalized or len(normalized) > 50:
            return None
        tag, _ = ArtifactTag.objects.get_or_create(artifact=self, name=normalized)
        return tag

    def remove_tag(self, name):
        self.artifact_tags.filter(name=name.strip().lower()).delete()

    def set_tags(self, names):
        normalized = {n.strip().lower() for n in names if n.strip()}
        self.artifact_tags.exclude(name__in=normalized).delete()
        for tag_name in normalized:
            if len(tag_name) <= 50:
                ArtifactTag.objects.get_or_create(artifact=self, name=tag_name)

    @property
    def web_type(self):
        return self.artifact_type in ["web_page", "raw_link"]

    @property
    def is_pdf(self):
        return self.artifact_type == "pdf"

    @property
    def reading_time_minutes(self):
        if not self.content:
            return 0
        clean_text = strip_tags(self.content)
        words = len(clean_text.split())
        return max(math.ceil(words / 200.0), 1)

    @property
    def type_icon(self):
        icons = {
            "web_page": "🌐",
            "raw_link": "🔗",
            "note": "📝",
            "quote": "💬",
            "image": "🖼️",
            "markdown": "📄",
            "pdf": "📕",
        }
        return icons.get(self.artifact_type, "📁")

    @property
    def type_label(self):
        dict_types = dict(self.TYPES)
        return dict_types.get(self.artifact_type, self.artifact_type.title())


class ArtifactTag(models.Model):
    artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="artifact_tags"
    )
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["artifact", "name"], name="unique_artifact_tag"
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower()
        super().save(*args, **kwargs)


class ArtifactHighlight(models.Model):
    STYLES = [
        ("yellow", "Yellow"),
        ("green", "Green"),
        ("blue", "Blue"),
        ("pink", "Pink"),
        ("red", "Red"),
    ]

    artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="highlights"
    )
    selected_text = models.TextField()
    note = models.TextField(blank=True, null=True)
    style = models.CharField(max_length=20, choices=STYLES, default="yellow")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Highlight ({self.style}): {self.selected_text[:30]}"

    @property
    def color_class(self):
        return f"highlight--{self.style}"


class ArtifactLink(models.Model):
    LINK_TYPES = [
        ("related", "Related"),
        ("supports", "Supports"),
        ("contradicts", "Contradicts"),
        ("background", "Background"),
        ("quotes", "Quotes"),
        ("depends_on", "Depends on"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="artifact_links"
    )
    source_artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="outgoing_links"
    )
    target_artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="incoming_links"
    )
    link_type = models.CharField(max_length=50, choices=LINK_TYPES, default="related")
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_artifact", "target_artifact"],
                name="unique_artifact_link",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_artifact.title} -> {self.target_artifact.title} ({self.link_type})"

    def clean(self):
        if self.source_artifact_id and self.target_artifact_id:
            if self.source_artifact_id == self.target_artifact_id:
                raise ValidationError("Cannot link an artifact to itself.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def type_label(self):
        dict_types = dict(self.LINK_TYPES)
        return dict_types.get(self.link_type, self.link_type.replace("_", " ").title())
