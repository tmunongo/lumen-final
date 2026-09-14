import hmac
import threading
from collections import defaultdict
from itertools import combinations

import httpx
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from lumen.models import Artifact, ArtifactHighlight, ArtifactLink, Project
from lumen.services.exporter import BibliographyExporter
from lumen.services.web_fetcher import fetch_artifact_content


# Auth Views
def login_view(request):
    if request.session.get("authenticated") is True:
        return redirect("projects_index")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        expected_username = getattr(settings, "LUMEN_USERNAME", "lumen")
        expected_password = getattr(settings, "LUMEN_PASSWORD", "")

        user_ok = hmac.compare_digest(username.lower(), expected_username.lower())
        pass_ok = hmac.compare_digest(password, expected_password)

        if user_ok and pass_ok:
            request.session.flush()
            request.session["authenticated"] = True
            request.session["username"] = username
            return_to = request.GET.get("return_to", reverse("projects_index"))
            return redirect(return_to if return_to.startswith("/") else "/")
        else:
            messages.error(request, "Invalid username or password.")
            return render(
                request,
                "sessions/new.html",
                {"error": "Invalid username or password."},
                status=200,
            )

    return render(request, "sessions/new.html")


def logout_view(request):
    request.session.flush()
    messages.info(request, "Signed out successfully.")
    return redirect("login")


# Project Views
def projects_index(request):
    sort_by = request.GET.get("sort", request.session.get("sort_by", "modified"))
    request.session["sort_by"] = sort_by

    show_archived_param = request.GET.get("show_archived")
    if show_archived_param is not None:
        show_archived = show_archived_param.lower() == "true"
        request.session["show_archived"] = show_archived
    else:
        show_archived = request.session.get("show_archived", False)

    query = request.GET.get("q", "").strip()

    qs = Project.objects.all()
    if not show_archived:
        qs = qs.active()

    if query:
        qs = qs.filter(name__icontains=query)

    if sort_by == "name":
        qs = qs.by_name()
    elif sort_by == "created":
        qs = qs.by_created()
    else:
        qs = qs.by_modified()

    context = {
        "projects": qs,
        "sort_by": sort_by,
        "show_archived": show_archived,
        "query": query,
    }
    return render(request, "projects/index.html", context)


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    artifacts = project.artifacts.all()

    type_filter = request.GET.get("type", "").strip()
    if type_filter:
        artifacts = artifacts.filter(artifact_type=type_filter)

    tag_filter = request.GET.get("tag", "").strip()
    if tag_filter:
        artifacts = artifacts.filter(artifact_tags__name=tag_filter.lower())

    query = request.GET.get("q", "").strip()
    if query:
        artifacts = artifacts.filter(title__icontains=query)

    artifacts = artifacts.recent()

    selected_artifact_id = request.GET.get("artifact_id")
    selected_artifact = None
    if selected_artifact_id:
        selected_artifact = artifacts.filter(id=selected_artifact_id).first()
    if not selected_artifact and artifacts.exists():
        selected_artifact = artifacts.first()

    context = {
        "project": project,
        "artifacts": artifacts,
        "selected_artifact": selected_artifact,
        "type_filter": type_filter,
        "tag_filter": tag_filter,
        "query": query,
    }
    return render(request, "projects/show.html", context)


def project_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            project = Project(name=name)
            try:
                project.save()
                messages.success(request, f"Project '{project.name}' created.")
                return redirect("project_detail", pk=project.pk)
            except Exception as e:
                messages.error(request, f"Failed to create project: {e}")
    return redirect("projects_index")


def project_archive(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.archive()
    messages.info(request, f"Project '{project.name}' archived.")
    return redirect("projects_index")


def project_unarchive(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.unarchive()
    messages.info(request, f"Project '{project.name}' unarchived.")
    return redirect("projects_index")


def project_export(request, pk):
    project = get_object_or_404(Project, pk=pk)
    fmt = request.GET.get("format", "markdown").lower()
    artifacts = project.artifacts.recent()

    if fmt == "csv":
        content = BibliographyExporter.export_csv(artifacts)
        filename = f"{project.name.lower().replace(' ', '_')}_export.csv"
        response = HttpResponse(content, content_type="text/csv")
    elif fmt == "json":
        content = BibliographyExporter.export_json(artifacts)
        filename = f"{project.name.lower().replace(' ', '_')}_export.json"
        response = HttpResponse(content, content_type="application/json")
    elif fmt == "bibtex":
        content = BibliographyExporter.export_bibtex(artifacts)
        filename = f"{project.name.lower().replace(' ', '_')}_export.bib"
        response = HttpResponse(content, content_type="text/x-bibtex")
    else:
        content = BibliographyExporter.export_markdown(artifacts)
        filename = f"{project.name.lower().replace(' ', '_')}_export.md"
        response = HttpResponse(content, content_type="text/markdown")

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# Artifact Views
def artifact_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        artifact_type = request.POST.get("artifact_type", "note")
        content = request.POST.get("content", "").strip()
        source_url = request.POST.get("source_url", "").strip()
        attribution = request.POST.get("attribution", "").strip()

        if not title and source_url:
            title = source_url

        artifact = Artifact(
            project=project,
            title=title,
            artifact_type=artifact_type,
            content=content,
            source_url=source_url or None,
            attribution=attribution or None,
        )
        try:
            artifact.save()
            if artifact.source_url:
                threading.Thread(
                    target=fetch_artifact_content, args=(artifact.id,), daemon=True
                ).start()

            messages.success(request, f"Artifact '{artifact.title}' created.")
            return redirect(
                f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
            )
        except Exception as e:
            messages.error(request, f"Failed to create artifact: {e}")

    return redirect("project_detail", pk=project.pk)


def artifact_delete(request, project_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=pk, project=project)
    artifact.delete()
    messages.info(request, "Artifact deleted.")
    return redirect("project_detail", pk=project.pk)


def artifact_fetch_content(request, project_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=pk, project=project)
    if artifact.source_url:
        threading.Thread(
            target=fetch_artifact_content, args=(artifact.id,), daemon=True
        ).start()
        messages.info(request, "Fetching latest content...")
    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
    )


def artifact_add_tag(request, project_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=pk, project=project)
    tag_name = request.POST.get("tag_name", "").strip()
    if tag_name:
        artifact.add_tag(tag_name)
    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
    )


def artifact_remove_tag(request, project_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=pk, project=project)
    tag_name = request.POST.get("tag_name", "").strip()
    if tag_name:
        artifact.remove_tag(tag_name)
    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
    )


def proxy_pdf(request, project_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=pk, project=project)

    if not artifact.source_url:
        raise Http404("No source URL")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; LumenSpace/1.0)"}
        resp = httpx.get(
            artifact.source_url, headers=headers, follow_redirects=True, timeout=30.0
        )
        if resp.status_code != 200:
            return HttpResponse("Failed to proxy PDF", status=502)
        content_type = resp.headers.get("content-type", "application/pdf")
        return HttpResponse(resp.content, content_type=content_type)
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=502)


# Highlight & Link Views
def highlight_create(request, project_id, artifact_id):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=artifact_id, project=project)

    if request.method == "POST":
        selected_text = request.POST.get("selected_text", "").strip()
        note = request.POST.get("note", "").strip()
        style = request.POST.get("style", "yellow").strip()

        if selected_text:
            ArtifactHighlight.objects.create(
                artifact=artifact,
                selected_text=selected_text,
                note=note or None,
                style=style,
            )
            messages.success(request, "Highlight added.")

    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
    )


def highlight_delete(request, project_id, artifact_id, pk):
    project = get_object_or_404(Project, pk=project_id)
    artifact = get_object_or_404(Artifact, pk=artifact_id, project=project)
    highlight = get_object_or_404(ArtifactHighlight, pk=pk, artifact=artifact)
    highlight.delete()
    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={artifact.id}"
    )


def link_create(request):
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        source_id = request.POST.get("source_artifact_id")
        target_id = request.POST.get("target_artifact_id")
        link_type = request.POST.get("link_type", "related")
        note = request.POST.get("note", "").strip()

        project = get_object_or_404(Project, pk=project_id)
        source = get_object_or_404(Artifact, pk=source_id, project=project)
        target = get_object_or_404(Artifact, pk=target_id, project=project)

        if source.id != target.id:
            ArtifactLink.objects.get_or_create(
                project=project,
                source_artifact=source,
                target_artifact=target,
                defaults={"link_type": link_type, "note": note or None},
            )
            messages.success(request, "Link created.")
        return redirect(
            f"{reverse('project_detail', kwargs={'pk': project.pk})}?artifact_id={source.id}"
        )
    return redirect("projects_index")


def link_delete(request, pk):
    link = get_object_or_404(ArtifactLink, pk=pk)
    project_id = link.project_id
    source_id = link.source_artifact_id
    link.delete()
    messages.info(request, "Link deleted.")
    return redirect(
        f"{reverse('project_detail', kwargs={'pk': project_id})}?artifact_id={source_id}"
    )


# Relationships Graph View
def relationships_index(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    artifacts = list(project.artifacts.recent())

    selected_id = request.GET.get("artifact_id")
    selected_artifact = None
    if selected_id:
        selected_artifact = next(
            (a for a in artifacts if str(a.id) == str(selected_id)), None
        )

    related, network, bridges, tag_suggestions = [], [], [], []
    if selected_artifact:
        all_tags_map = {a.id: set(a.tag_names) for a in artifacts}
        related = _compute_related(selected_artifact, all_tags_map, artifacts)
        network = _compute_network(selected_artifact, all_tags_map, artifacts)
        bridges = _compute_bridges(artifacts)
        tag_suggestions = _suggest_tags(selected_artifact, related)

    context = {
        "project": project,
        "artifacts": artifacts,
        "selected_artifact": selected_artifact,
        "related": related,
        "network": network,
        "bridges": bridges,
        "tag_suggestions": tag_suggestions,
    }
    return render(request, "relationships/index.html", context)


def _compute_related(anchor, all_tags_map, all_artifacts):
    anchor_tags = set(anchor.tag_names)
    if not anchor_tags:
        return []
    results = []
    for candidate in all_artifacts:
        if candidate.id == anchor.id:
            continue
        c_tags = all_tags_map.get(candidate.id, set())
        shared = anchor_tags & c_tags
        if not shared:
            continue
        union = anchor_tags | c_tags
        strength = len(shared) / float(len(union))
        results.append(
            {
                "artifact": candidate,
                "shared_tags": list(shared),
                "strength": strength,
            }
        )
    return sorted(results, key=lambda x: x["strength"], reverse=True)


def _compute_network(start, all_tags_map, all_artifacts):
    visited = set()
    queue = [start]
    network = []
    while queue:
        current = queue.pop(0)
        if current.id in visited:
            continue
        visited.add(current.id)
        network.append(current)
        related = _compute_related(current, all_tags_map, all_artifacts)
        for r in related:
            if r["artifact"].id not in visited:
                queue.append(r["artifact"])
    return network


def _compute_bridges(all_artifacts):
    cooc = defaultdict(lambda: defaultdict(int))
    for art in all_artifacts:
        tags = art.tag_names
        if len(tags) < 2:
            continue
        for t1, t2 in combinations(tags, 2):
            cooc[t1][t2] += 1
            cooc[t2][t1] += 1

    bridges = []
    for art in all_artifacts:
        tags = art.tag_names
        if len(tags) < 2:
            continue
        pairs = list(combinations(tags, 2))
        total = sum(cooc[t1][t2] for t1, t2 in pairs)
        avg = total / float(len(pairs))
        if avg < 2.0:
            bridges.append(art)
    return bridges


def _suggest_tags(anchor, related):
    if not related:
        return []
    current_tags = set(anchor.tag_names)
    suggestions = {}
    for r in related:
        weight = round(r["strength"] * 10)
        for tag in r["artifact"].tag_names:
            if tag not in current_tags:
                suggestions[tag] = suggestions.get(tag, 0) + weight
    sorted_sug = sorted(suggestions.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_sug[:5]]
