import csv
import io
import json
import re


class BibliographyExporter:
    @classmethod
    def export_markdown(cls, artifacts):
        sections = ["# Bibliography\n"]
        for idx, art in enumerate(artifacts, 1):
            buf = [f"## {idx}. {art.title}"]
            if art.source_url:
                buf.append(f"**URL:** {art.source_url}")
            if art.attribution:
                buf.append(f"**Attribution:** {art.attribution}")
            buf.append(f"**Type:** {art.type_label}")
            tags = art.tag_names
            if tags:
                buf.append(f"**Tags:** {', '.join(tags)}")
            if art.content:
                buf.append(f"\n{art.content}")
            sections.append("\n".join(buf))
        return "\n\n".join(sections)

    @classmethod
    def export_csv(cls, artifacts):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "URL", "Type", "Created At", "Tags"])
        for art in artifacts:
            created_str = (
                art.created_at.isoformat() if getattr(art, "created_at", None) else ""
            )
            tags_str = ", ".join(art.tag_names)
            writer.writerow(
                [
                    art.title,
                    art.source_url or "",
                    art.artifact_type,
                    created_str,
                    tags_str,
                ]
            )
        return output.getvalue()

    @classmethod
    def export_json(cls, artifacts):
        data = []
        for art in artifacts:
            created_str = (
                art.created_at.isoformat() if getattr(art, "created_at", None) else ""
            )
            data.append(
                {
                    "title": art.title,
                    "url": art.source_url,
                    "type": art.artifact_type,
                    "created_at": created_str,
                    "tags": art.tag_names,
                }
            )
        return json.dumps(data, indent=2)

    @classmethod
    def export_bibtex(cls, artifacts):
        entries = []
        for idx, art in enumerate(artifacts, 1):
            key = cls._generate_bibtex_key(art, idx)
            safe_title = cls._sanitize_bibtex(art.title)
            safe_url = cls._sanitize_bibtex(art.source_url or "")
            entry = [
                f"@misc{{{key},",
                f"  title = {{{safe_title}}},",
            ]
            if safe_url:
                entry.append(f"  url = {{{safe_url}}},")
            entry.append(f"  note = {{Type: {art.artifact_type}}}")
            entry.append("}")
            entries.append("\n".join(entry))
        return "\n\n".join(entries)

    @classmethod
    def _generate_bibtex_key(cls, artifact, idx):
        clean_title = re.sub(r"[^\w\s]", "", artifact.title or "").lower().split()
        base = "_".join(clean_title[:3]) if clean_title else "link"
        return f"{base}_{idx}"

    @classmethod
    def _sanitize_bibtex(cls, text):
        if not text:
            return ""
        return (
            text.replace("{", "\\{")
            .replace("}", "\\}")
            .replace("#", "\\#")
            .replace("$", "\\$")
        )
