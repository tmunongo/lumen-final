[![CI](https://github.com/tmunongo/lumen-space/actions/workflows/ci.yml/badge.svg)](https://github.com/tmunongo/lumen-space/actions/workflows/ci.yml)

# ◉ Lumen Space

> A local-first tool for deep research and structured thinking — Python 3.14 & Django Edition.

Lumen Space is a self-hosted research companion that helps you capture, connect, and make sense of information. It supports web pages, notes, quotes, markdown documents, highlights, tags, and a semantic relationship graph.

This version is a full **Python 3.14 & Django** port using **`django-cotton`** for UI component architecture, **`Alpine.js`** for reactive frontend interactions, **`uv`** for lightning-fast package management, and SQLite 3 for zero-config self-hosting.

---

## Features

- 📁 **Projects** — Organize research into isolated workspaces
- 🌐 **Web Artifacts** — Paste a URL; Lumen fetches and stores article text in the background
- 📝 **Notes, Quotes & Markdown Docs** — Rich text capture with attribution and sourcing
- 🏷️ **Tags** — Lightweight, multi-tag taxonomy per artifact
- 🖊️ **Highlights** — Select text in the reader and save color-coded highlights
- ⬡ **Relationships** — Semantic graph powered by tag co-occurrence — discover bridge artifacts and get tag suggestions automatically
- 🔒 **Single-User Auth** — Optional HTTP authentication (`LUMEN_USERNAME` / `LUMEN_PASSWORD`)
- 🧩 **Django Cotton UI Components** — Modular `<c-project-item>`, `<c-reader>`, `<c-tags>` components
- ⚡ **Alpine.js & HTMX** — Fast, reactive user interactions without complex single-page apps

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.14 |
| Framework | Django 6 |
| Package Manager | `uv` |
| UI Components | `django-cotton` |
| Frontend Interactivity | Alpine.js + HTMX + Vanilla CSS |
| Database | SQLite 3 (single-file, zero config) |
| Web Scraping | BeautifulSoup4 + `httpx` + `nh3` (sanitization) |
| Markdown | `markdown` |
| Testing & Linting | `pytest`, `pytest-django`, `ruff`, `black` |
| Production Server | Gunicorn |

---

## Quick Start — Local CLI

### Prerequisites

- Python ≥ 3.14
- `uv` package manager (`curl -sSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)

### Steps

```bash
# Clone
git clone https://github.com/tmunongo/lumen-django.git
cd lumen-django

# Sync virtualenv & dependencies
uv sync

# Run database migrations
uv run python manage.py migrate

# Start dev server (http://127.0.0.1:8000)
uv run python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Default login credentials are **`lumen` / `lumen`**.

#### Optional: Basic Auth Configuration

Set environment variables before starting:

```bash
LUMEN_USERNAME=me LUMEN_PASSWORD=secret uv run python manage.py runserver
```

To disable authentication completely:

```bash
LUMEN_AUTH_DISABLED=true uv run python manage.py runserver
```

---

## Self-Hosting via Docker Compose

Recommended for production deployment on any server.

### 1. `docker-compose.yml`

```yaml
services:
  lumen:
    image: ghcr.io/tmunongo/lumen-django:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      SECRET_KEY_BASE: "${SECRET_KEY_BASE:-change-me-in-production}"
      LUMEN_USERNAME: "${LUMEN_USERNAME:-lumen}"
      LUMEN_PASSWORD: "${LUMEN_PASSWORD:-lumen}"
      LUMEN_AUTH_DISABLED: "${LUMEN_AUTH_DISABLED:-false}"
    volumes:
      - lumen_storage:/app/storage

volumes:
  lumen_storage:
```

### 2. Start container

```bash
docker compose up -d
```

---

## Development & Testing

```bash
# Run test suite
uv run pytest

# Run linting
uv run ruff check .

# Check code formatting
uv run black --check .

# Auto-format code
make format
```

### Version Bumping & Releases

Versions follow [Semantic Versioning](https://semver.org). Use `make` commands to bump versions:

```bash
make bump-patch   # 0.1.0 → 0.1.1 (bug fixes)
make bump-minor   # 0.1.0 → 0.2.0 (new features)
make bump-major   # 0.1.0 → 1.0.0 (breaking changes)
```

Each command:
1. Verifies a clean working tree
2. Bumps version in `VERSION` file
3. Commits and creates tag `vX.Y.Z`
4. Pushes tag to GitHub, triggering CI/CD release workflow

---

## Project Structure

```
lumen-django/
├── config/                 # Django settings & URL routing
├── lumen/
│   ├── models.py           # Project, Artifact, ArtifactTag, ArtifactHighlight, ArtifactLink
│   ├── views.py            # Projects, artifacts, highlights, links & relationships views
│   ├── middleware.py       # Single-user auth middleware
│   ├── services/           # BibliographyExporter & WebFetcher
│   └── tests/              # Pytest unit & integration test suite
├── static/css/             # Application design system CSS
├── templates/
│   ├── base.html           # Main page layout
│   ├── cotton/             # Django Cotton UI components (<c-reader>, <c-tags>, etc.)
│   ├── projects/           # Project index and workspace detail pages
│   └── relationships/      # Semantic graph visualization page
├── Dockerfile              # Production multi-stage Docker build
├── Makefile                # Development & release helpers
└── VERSION                 # Single source of truth version file
```

---

## License

MIT — see [LICENSE](LICENSE).
