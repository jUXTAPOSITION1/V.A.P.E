"""
VAPE investigation report -> PDF. Keyless, local, no external service: fpdf2
renders directly from the same evidence dict investigate.py's write_report()
already assembles for the Markdown report, so the two can never disagree.

Visual language matches docs/assets/report.js (the client-side x402 hire-flow
report generator) — same letterhead treatment, verdict badge colors, and
section layout — so a report reads as "the same VAPE" whether it came from
a paid x402 call or an autonomous investigation.
"""
import os

from fpdf import FPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATAR_PATH = os.path.join(ROOT, "docs", "assets", "vape-avatar.jpg")

CYAN = (34, 211, 238)
EMERALD = (16, 185, 129)
AMBER = (251, 191, 36)
ROSE = (251, 113, 133)
INK = (24, 24, 27)
MUTED = (113, 113, 122)
LETTERHEAD_BG = (9, 9, 11)

VERDICT_COLOR = {"PROCEED": EMERALD, "CAUTION": AMBER, "REJECT": ROSE}
VERDICT_LABEL = {"PROCEED": "GO", "CAUTION": "CAUTION", "REJECT": "NO-GO"}


class _VapeReportPDF(FPDF):
    def __init__(self, disclaimer):
        super().__init__(unit="pt", format="Letter")
        self._disclaimer = disclaimer
        self.set_auto_page_break(auto=True, margin=64)
        self.add_page()

    def footer(self):
        self.set_y(-56)
        self.set_draw_color(230, 230, 235)
        self.set_line_width(0.5)
        self.line(48, self.get_y(), self.w - 48, self.get_y())
        self.set_y(-42)
        self.set_font("helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.multi_cell(self.w - 96, 10, self._disclaimer, align="L")
        self.set_font("helvetica", "", 7.5)
        self.text(48, self.h - 28, f"VAPE Investigation Report · Page {self.page_no()} · Real on-chain data, keyless recon")


def _safe(value):
    """Base PDF fonts (helvetica) only support Latin-1 — live API data (token
    names/symbols especially) can contain arbitrary Unicode at any time, so
    replace anything outside that range rather than crashing report generation."""
    return str(value).encode("latin-1", errors="replace").decode("latin-1")


def _kv_row(pdf, label, value, link=None, label_w=140):
    pdf.set_font("helvetica", "B", 9.5)
    pdf.set_text_color(*INK)
    pdf.cell(label_w, 14, _safe(f"{label}:"))
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*(CYAN if link else MUTED))
    pdf.cell(0, 14, _safe(value), link=link, new_x="LMARGIN", new_y="NEXT")


def _section_heading(pdf, title):
    pdf.ln(6)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 14, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(220, 220, 225)
    pdf.set_line_width(0.75)
    pdf.line(48, pdf.get_y(), pdf.w - 48, pdf.get_y())
    pdf.ln(6)


def build_investigation_pdf(pdf_path, target, chain, sym, verdict, score, reasons,
                             gp, dex, onchain, verif, corr, generated_iso):
    disclaimer = ("Real on-chain data. Independently verifiable via GoPlus, DexScreener, "
                  "Base RPC, and Etherscan V2. Not investment advice.")
    pdf = _VapeReportPDF(disclaimer)
    margin = 48

    # ── Letterhead ──────────────────────────────────────────────
    pdf.set_fill_color(*LETTERHEAD_BG)
    pdf.rect(0, 0, pdf.w, 96, style="F")
    if os.path.exists(AVATAR_PATH):
        try:
            pdf.image(AVATAR_PATH, x=margin, y=20, w=56, h=56)
        except Exception:
            pass
    pdf.set_xy(margin + 68, 22)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 24, "V.A.P.E.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(margin + 68, 48)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*CYAN)
    pdf.cell(0, 14, "AUTONOMOUS ON-CHAIN DETECTIVE  ·  ERC-8004 #59900  ·  BASE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(margin + 68, 62)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(160, 160, 165)
    pdf.cell(0, 14, "github.com/jUXTAPOSITION1/V.A.P.E", link="https://github.com/jUXTAPOSITION1/V.A.P.E", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(margin, 128)
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(*INK)
    pdf.cell(0, 18, "INVESTIGATION REPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*CYAN)
    pdf.set_line_width(1.5)
    pdf.line(margin, pdf.get_y() + 2, margin + 90, pdf.get_y() + 2)
    pdf.ln(20)

    pdf.set_x(margin)
    _kv_row(pdf, "Target", f"{sym} ({target})", link=f"https://basescan.org/address/{target}")
    pdf.set_x(margin)
    _kv_row(pdf, "Chain", f"{chain} (Base)")
    pdf.set_x(margin)
    _kv_row(pdf, "Generated", generated_iso)
    pdf.set_x(margin)
    _kv_row(pdf, "Safety score", f"{score}/100")

    # ── Verdict badge ───────────────────────────────────────────
    pdf.ln(10)
    color = VERDICT_COLOR.get(verdict, MUTED)
    pdf.set_fill_color(*color)
    pdf.set_xy(margin, pdf.get_y())
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(*INK)
    pdf.cell(140, 28, _safe(VERDICT_LABEL.get(verdict, verdict)), align="C", fill=True)
    pdf.ln(40)

    # ── Verdict rationale ────────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "VERDICT RATIONALE")
    pdf.set_x(margin)
    pdf.set_font("helvetica", "", 9.5)
    if reasons:
        for r in reasons:
            pdf.set_x(margin)
            pdf.set_text_color(*ROSE)
            pdf.cell(12, 13, "-")
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(pdf.w - margin * 2 - 12, 13, _safe(r))
    else:
        pdf.set_x(margin)
        pdf.set_text_color(*EMERALD)
        pdf.multi_cell(pdf.w - margin * 2, 13, "No risk penalties triggered - clean across all automated checks.")

    # ── Market & liquidity ───────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "MARKET & LIQUIDITY (DEXSCREENER)")
    pdf.set_x(margin)
    if dex:
        rows = [
            ("Symbol / Name", f"{dex.get('symbol')} / {dex.get('name')}"),
            ("Price", f"${dex.get('price_usd')}"),
            ("Liquidity", f"${dex.get('liquidity_usd')}"),
            ("24h Volume", f"${dex.get('vol_24h_usd')}"),
            ("24h Change", f"{dex.get('change_24h_pct')}%"),
            ("DEX", dex.get("dex")),
        ]
        for k, v in rows:
            pdf.set_x(margin)
            _kv_row(pdf, k, v)
    else:
        pdf.set_x(margin)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(pdf.w - margin * 2, 13, "No DEX pair data (illiquid / not listed).")

    # ── Token security ───────────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "TOKEN SECURITY (GOPLUS)")
    pdf.set_x(margin)
    if gp:
        for k in ("is_honeypot", "buy_tax", "sell_tax", "is_mintable", "is_proxy",
                  "can_take_back_ownership", "owner_change_balance", "hidden_owner",
                  "cannot_sell_all", "owner_address"):
            if k in gp:
                pdf.set_x(margin)
                _kv_row(pdf, k.replace("_", " ").title(), gp.get(k))
    else:
        pdf.set_x(margin)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(pdf.w - margin * 2, 13, "GoPlus returned no security profile for this token.")

    # ── On-chain presence ────────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "ON-CHAIN PRESENCE (BASE RPC)")
    pdf.set_x(margin)
    if onchain.get("is_contract") is None:
        _kv_row(pdf, "Is contract", f"unavailable this cycle ({onchain.get('error', 'RPC call failed')})")
    else:
        _kv_row(pdf, "Is contract", onchain.get("is_contract"))
        pdf.set_x(margin)
        _kv_row(pdf, "Code size", f"{onchain.get('code_size_bytes')} bytes")

    # ── Contract verification ────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "CONTRACT VERIFICATION")
    pdf.set_x(margin)
    if verif.get("checked"):
        _kv_row(pdf, "Verified", verif.get("verified"))
        pdf.set_x(margin)
        _kv_row(pdf, "Name / Compiler", f"{verif.get('name')} / {verif.get('compiler')}")
        pdf.set_x(margin)
        _kv_row(pdf, "Proxy / Impl.", f"{verif.get('proxy')} / {verif.get('implementation')}")
    else:
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(pdf.w - margin * 2, 13, _safe(verif.get("note", "not checked")))

    # ── Threat correlation ───────────────────────────────────────
    pdf.set_x(margin)
    _section_heading(pdf, "THREAT CORRELATION")
    pdf.set_x(margin)
    pdf.set_font("helvetica", "", 9.5)
    if corr:
        for c in corr:
            pdf.set_x(margin)
            pdf.set_text_color(*ROSE)
            pdf.cell(12, 13, "-")
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(pdf.w - margin * 2 - 12, 13, _safe(c))
    else:
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(pdf.w - margin * 2, 13, "No correlation to recent exploit techniques.")

    pdf.output(pdf_path)
    return pdf_path
