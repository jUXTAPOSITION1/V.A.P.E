#!/usr/bin/env python3
"""
Shared VAPE report-formatting helpers — the "house style" for every generated
markdown report and broadcast (agents/investigate.py, agents/broadcast.py,
and anything else that publishes to intel/): one consistent letterhead
(VAPE's own avatar — the same image already used as the PDF letterhead in
agents/report_pdf.py and the site's nav/footer mark) and a plain-text
verdict stamp instead of colored-circle emoji. This reads as a security
dossier, not a chat message — no traffic-light emoji anywhere in a
published report.
"""

REPO_RAW_BASE = "https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main"
AVATAR_URL = f"{REPO_RAW_BASE}/docs/assets/vape-avatar.jpg"

VERDICT_LABEL = {"PROCEED": "PROCEED", "CAUTION": "CAUTION", "REJECT": "REJECT"}


def letterhead_md(title):
    """VAPE's real avatar floated beside the report title, GitHub-flavored-
    markdown letterhead — the one consistent visual signature across every
    surface VAPE publishes to (site, PDF, and now every markdown report).
    Returns a list of lines ready to extend() into a report's line buffer."""
    return [
        f'<img src="{AVATAR_URL}" width="56" height="56" align="left" '
        'style="border-radius:10px;margin-right:14px" alt="VAPE" />',
        "",
        f"# {title}",
        "",
        '<br clear="left"/>',
        "",
    ]


def verdict_stamp(verdict, extra=None):
    """A plain-text classification line — no colored-circle emoji. `extra`
    is an optional trailing detail (e.g. a safety score) appended after a
    middle dot."""
    label = VERDICT_LABEL.get(verdict, verdict or "UNKNOWN")
    line = f"> **VERDICT — {label}**"
    if extra:
        line += f" · {extra}"
    return line
