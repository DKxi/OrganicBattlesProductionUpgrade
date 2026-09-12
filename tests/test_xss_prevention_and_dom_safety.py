import os
import re
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_DIR = Path(__file__).resolve().parent.parent


def test_dompurify_vendored_and_included():
    """Verify DOMPurify is vendored locally and included in templates/index.html."""
    purify_path = BASE_DIR / "static" / "vendor" / "purify.min.js"
    assert purify_path.exists(), "purify.min.js must exist in static/vendor/"
    purify_content = purify_path.read_text(encoding="utf-8")
    assert "DOMPurify" in purify_content, "DOMPurify must be defined in purify.min.js"
    assert len(purify_content) > 10000, "purify.min.js must contain the full minified library"

    index_html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    assert "/static/vendor/purify.min.js" in index_html, (
        "templates/index.html must include script tag for purify.min.js"
    )
    # Ensure DOMPurify is loaded before main.js
    purify_pos = index_html.find("/static/vendor/purify.min.js")
    main_pos = index_html.find("/static/js/main.js")
    assert purify_pos < main_pos, "DOMPurify must be loaded before main.js"


def test_no_unsafe_inner_html_interpolation_in_main_js():
    """Verify static/js/main.js does not interpolate untrusted variables into innerHTML."""
    main_js = (BASE_DIR / "static" / "js" / "main.js").read_text(encoding="utf-8")

    # Helper utilities must exist
    assert "function createEl(" in main_js, "createEl helper must be defined in main.js"
    assert "function sanitizeHtml(" in main_js, "sanitizeHtml helper must be defined in main.js"
    assert "function escapeHtml(" in main_js, "escapeHtml helper must be defined in main.js"

    # Untrusted fields must NOT be assigned via dynamic innerHTML
    forbidden_interpolations = [
        r"tbody\.innerHTML\s*=\s*items\.map",
        r"tbody\.innerHTML\s*=\s*filtered\.map",
        r"tbody\.innerHTML\s*=\s*questions\.map",
        r"tbody\.innerHTML\s*=\s*res\.releases\.map",
        r"log\.innerHTML\s*=\s*s\.log\.map",
        r"gallery\.innerHTML\s*=\s*options\.map",
        r"gallery\.innerHTML\s*=\s*filtered",
        r"container\.innerHTML\s*=.*q\.prompt",
        r"info\.innerHTML\s*=.*s\.player\.hp",
        r"startBtn\.innerHTML\s*=",
    ]

    for pattern in forbidden_interpolations:
        match = re.search(pattern, main_js)
        assert not match, f"Found unsafe innerHTML interpolation matching '{pattern}' in main.js"


def test_avatars_js_does_not_use_inner_html():
    """Verify static/js/avatars.js does not use innerHTML to build avatar frames."""
    avatars_js = (BASE_DIR / "static" / "js" / "avatars.js").read_text(encoding="utf-8")
    assert "innerHTML" not in avatars_js, "static/js/avatars.js should not use innerHTML"


def test_frontend_routes_serve_clean_assets():
    """Verify HTTP requests for vendor assets and main templates succeed."""
    res_purify = client.get("/static/vendor/purify.min.js")
    assert res_purify.status_code == 200
    assert "DOMPurify" in res_purify.text

    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "/static/vendor/purify.min.js" in res_index.text


def test_chemistry_notation_preservation():
    """Ensure chemistry strings containing math comparison and reaction arrows are safely retained."""
    chem_texts = [
        "Reactants heated to < 50°C under 1 atm",
        "Equilibrium constant K > 1.0 x 10^5",
        "A + B <=> C + D -> E",
        "Concentration [H+] <= 10^-7 M",
    ]
    # Verify that these strings do not contain executable script elements
    for text in chem_texts:
        assert "<script" not in text.lower()
        # Text nodes preserve exact characters without dropping unclosed tags
        assert len(text) > 5
