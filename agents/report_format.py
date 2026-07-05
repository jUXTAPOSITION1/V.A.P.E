#!/usr/bin/env python3
"""
Shared VAPE report-formatting helpers — the "house style" for every generated
markdown report and broadcast (agents/investigate.py, agents/broadcast.py,
agents/run.py, and anything else that publishes to intel/ or reports/): one
consistent letterhead (VAPE's own avatar — the same image already used as
the PDF letterhead in agents/report_pdf.py and the site's nav/footer mark),
a violet "VAPE · autonomous system" identity badge, and verdict/score
badges rendered via shields.io using the exact same colors the live site
uses for PROCEED/CAUTION/REJECT (docs/assets/app.js's `_verdictColor`) — a
numeric score gets a genuine color *gradient* (continuously interpolated
across rose -> amber -> emerald, not one of three fixed buckets), so a 51
and a 79 render as visibly different shades even though both are
technically "above the CAUTION line." No colored-circle/face emoji anywhere
in a published report — this reads as a security dossier, not a chat
message.
"""

REPO_RAW_BASE = "https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main"
AVATAR_URL = f"{REPO_RAW_BASE}/docs/assets/vape-avatar.jpg"

VERDICT_LABEL = {"PROCEED": "PROCEED", "CAUTION": "CAUTION", "REJECT": "REJECT"}

# Exact hex values from docs/assets/app.js's _verdictColor() / site.css — one
# color vocabulary shared by the live site and every generated report, so a
# REJECT reads as the same rose everywhere VAPE publishes.
ROSE = (0xFB, 0x71, 0x85)      # #fb7185 — REJECT / HIGH / CRITICAL
AMBER = (0xFB, 0xBF, 0x24)     # #fbbf24 — CAUTION / MEDIUM
EMERALD = (0x10, 0xB9, 0x81)   # #10b981 — PROCEED / LOW
ZINC = (0xA1, 0xA1, 0xAA)      # #a1a1aa — unknown/neutral
VIOLET = "8B5CF6"              # tasteful accent for VAPE's own identity badge —
                                # matches the site's "Autonomous Engineering"/
                                # Development Ledger violet, used sparingly

SITE_COLORS = {"PROCEED": EMERALD, "CAUTION": AMBER, "REJECT": ROSE}


def _hex(rgb):
    return "%02X%02X%02X" % rgb


def _lerp_rgb(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def score_color_hex(score):
    """Continuous rose -> amber -> emerald gradient for a 0-100 score —
    a 45 and a 55 land on visibly different colors either side of the
    CAUTION line, not the same flat bucket color."""
    score = max(0, min(100, score))
    if score <= 50:
        return _hex(_lerp_rgb(ROSE, AMBER, score / 50))
    return _hex(_lerp_rgb(AMBER, EMERALD, (score - 50) / 50))


def _shield_escape(s):
    """shields.io's static-badge escaping: literal '-' and '_' must be
    doubled, spaces become '_', and '/' must be percent-encoded or it's
    read as an extra URL path segment (e.g. a "92/100" score badge)."""
    return str(s).replace("-", "--").replace("_", "__").replace(" ", "_").replace("/", "%2F")


def _badge_md(label, message, hex_color, alt=None):
    l = _shield_escape(label)
    m = _shield_escape(message)
    return f'![{alt or message}](https://img.shields.io/badge/{l}-{m}-{hex_color}?style=flat-square)'


def verdict_badge(verdict):
    """A shields.io badge in the exact site color for this verdict — the
    markdown-report equivalent of the colored pill the site renders for the
    same verdict string."""
    label = VERDICT_LABEL.get(verdict, verdict or "UNKNOWN")
    color = _hex(SITE_COLORS.get(verdict, ZINC))
    return _badge_md("VERDICT", label, color)


def score_badge(score, label="SAFETY SCORE"):
    """A shields.io badge whose color is a live point on the rose->amber->
    emerald gradient at this exact score — see score_color_hex()."""
    return _badge_md(label, f"{score}/100", score_color_hex(score), alt=f"{score}/100")


def vape_badge():
    """A small, tasteful violet identity badge — VAPE's own accent color
    (matches the site's Development Ledger / "Autonomous Engineering"
    treatment), used once per report as part of the letterhead rather than
    scattered throughout."""
    return _badge_md("VAPE", "autonomous system", VIOLET)


def letterhead_md(title):
    """VAPE's real avatar floated beside the report title, GitHub-flavored-
    markdown letterhead — the one consistent visual signature across every
    surface VAPE publishes to (site, PDF, and now every markdown report),
    with a small violet identity badge underneath the title.
    Returns a list of lines ready to extend() into a report's line buffer."""
    return [
        f'<img src="{AVATAR_URL}" width="56" height="56" align="left" '
        'style="border-radius:10px;margin-right:14px" alt="VAPE" />',
        "",
        f"# {title}",
        "",
        vape_badge(),
        "",
        '<br clear="left"/>',
        "",
    ]


def verdict_stamp(verdict, score=None):
    """The verdict line for a report header: a colored VERDICT badge, plus
    a gradient SAFETY SCORE badge when a numeric score is available. Pass
    the raw number, not a pre-formatted string — this needs the real value
    to compute the gradient color."""
    parts = [verdict_badge(verdict)]
    if score is not None:
        parts.append(score_badge(score))
    return " ".join(parts)
