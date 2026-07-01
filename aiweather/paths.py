"""Filesystem paths for AI Weather static assets."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PACKAGE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = STATIC_DIR / "templates"
INDEX_HTML = STATIC_DIR / "index.html"
ERROR_TEMPLATE = TEMPLATES_DIR / "error.html"
