"""Generate a self-contained, interactive HTML results dashboard.

Reads whatever the pipeline has written into ``results/`` (figures, CSV tables,
the interactive brain viewers) and assembles one portable, theme-aware web page
that conveys the *depth* of the analysis: tabbed brain galleries (glass-brain,
slices, inflated surface, axial montage, and a live volume viewer), chart-style
robustness diagnostics, the recognition/recall contrast maps, and short
plain-language captions under every image explaining what it shows and how to
read it. Everything is inlined (images as base64, viewers via iframe ``srcdoc``)
so the file has no external dependencies.

Design: a scholarly-instrument look — serif headings + system UI, cerebral-blue
primary with a sparing "activation amber" accent from the hot end of an fMRI
colormap, semantic green/amber/red for diagnostic robustness. Light and dark are
both defined via CSS custom properties.
"""
from __future__ import annotations

import base64
import html
import logging
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)

# Embed interactive viewers up to this size (bytes); larger ones are skipped to
# keep the page portable (the 3-D surface viewer can be several MB).
_MAX_EMBED = 1_400_000


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _img_uri(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _table_html(df: Optional[pd.DataFrame], cols=None, max_rows=None,
                numeric_round=2) -> str:
    if df is None or len(df) == 0:
        return '<p class="muted">Not available.</p>'
    d = df.copy()
    if cols:
        d = d[[c for c in cols if c in d.columns]]
    if max_rows:
        d = d.head(max_rows)
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(numeric_round)
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in d.columns)
    body = []
    for _, row in d.iterrows():
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in row.tolist())
        body.append(f"<tr>{cells}</tr>")
    return (f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _chip(label: str, value: str) -> str:
    return (f'<div class="chip"><span class="chip-value">{html.escape(value)}</span>'
            f'<span class="chip-label">{html.escape(label)}</span></div>')


def _cap(text: str) -> str:
    return f'<p class="cap">{text}</p>'


def _fig_block(uri: Optional[str], caption_html: str) -> Optional[str]:
    if not uri:
        return None
    return (f'<div class="figblock"><img src="{uri}" loading="lazy" alt="">'
            f'{caption_html}</div>')


def _iframe_block(path: Path, caption_html: str) -> Optional[str]:
    if not path.exists() or path.stat().st_size > _MAX_EMBED:
        return None
    srcdoc = html.escape(path.read_text(), quote=True)
    return (f'<div class="figblock"><iframe class="viewer-frame" srcdoc="{srcdoc}" '
            f'title="Interactive viewer"></iframe>{caption_html}</div>')


_LAZY_SEQ = 0


def _lazy_viewer_block(path: Path, caption_html: str, btn_label: str) -> Optional[str]:
    """A heavy interactive viewer (e.g. the multi-MB 3-D surface) held inert in a
    <template> and rendered only when the user clicks — keeps the page snappy."""
    global _LAZY_SEQ
    if not path.exists():
        return None
    _LAZY_SEQ += 1
    tid = f"lazy{_LAZY_SEQ}"
    srcdoc = html.escape(path.read_text(), quote=True)
    return (f'<div class="figblock">'
            f'<button class="loadbtn" data-tpl="{tid}">{html.escape(btn_label)}</button>'
            f'<template id="{tid}"><iframe class="viewer-frame" style="height:600px" '
            f'srcdoc="{srcdoc}" title="3-D viewer"></iframe></template>'
            f'<div class="lazy-slot" id="{tid}-slot"></div>{caption_html}</div>')


_TAB_SEQ = 0


def _tabs(items: List[Tuple[str, Optional[str]]]) -> str:
    """A tabbed gallery. `items` = [(label, panel_html_or_None), ...]; panels
    that are None (missing figure) are dropped."""
    global _TAB_SEQ
    items = [(lbl, pan) for lbl, pan in items if pan]
    if not items:
        return '<p class="muted">No figures available.</p>'
    _TAB_SEQ += 1
    gid = f"tabs{_TAB_SEQ}"
    buttons, panels = [], []
    for i, (label, panel) in enumerate(items):
        active = " active" if i == 0 else ""
        buttons.append(
            f'<button class="tab{active}" data-g="{gid}" data-i="{i}" '
            f'role="tab">{html.escape(label)}</button>')
        panels.append(f'<div class="tabpanel{active}" data-g="{gid}" '
                      f'data-i="{i}">{panel}</div>')
    return (f'<div class="tabs"><div class="tabbar" role="tablist">'
            f'{"".join(buttons)}</div><div class="tabpanels">'
            f'{"".join(panels)}</div></div>')


# --------------------------------------------------------------------------
# Diagnostics summary (reload from CSVs)
# --------------------------------------------------------------------------
def _diagnostics_summary(tables: Path):
    from . import report
    focus = _read_csv(tables / "diagnostics_focus_counter.csv")
    jk = _read_csv(tables / "diagnostics_jackknife.csv")
    clust = _read_csv(tables / "diagnostics_clusters.csv")
    diag = {}
    if focus is not None:
        diag["focus_counter"] = focus
    if jk is not None:
        diag["jackknife"] = jk
    if clust is not None:
        diag["cluster_table"] = clust
    if not diag:
        return None
    return report._diagnostics_summary(diag)


def _diagnostics_table_html(summary: Optional[pd.DataFrame]) -> str:
    if summary is None or len(summary) == 0:
        return '<p class="muted">Diagnostics not available.</p>'
    rows = []
    for _, r in summary.iterrows():
        n = int(r.get("n experiments (focus)", 0) or 0)
        infl = float(r.get("max single-study influence", 0) or 0)
        if n >= 50 and infl <= 0.05:
            sev, tag = "good", "robust"
        elif n >= 25 and infl <= 0.10:
            sev, tag = "warn", "moderate"
        else:
            sev, tag = "crit", "fragile"
        region = html.escape(str(r.get("region", "") or ""))
        rows.append(
            f'<tr><td>{html.escape(str(r["cluster"]))}</td><td>{region}</td>'
            f'<td class="num">{n}</td><td class="num">{infl:.3f}</td>'
            f'<td><span class="pill pill-{sev}">{tag}</span></td></tr>')
    return ('<div class="table-wrap"><table><thead><tr>'
            '<th>cluster</th><th>region</th><th>experiments</th>'
            '<th>max single-study influence</th><th>robustness</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _advanced_section(cfg: Config) -> str:
    """Extended analyses that raise the study to research level: encoding vs.
    retrieval, quantitative default-mode-network overlap, and recovery of the
    canonical recollection-network landmarks."""
    import json
    figs = cfg.path("figures")
    tables = cfg.path("tables")

    def uri(name):
        return _img_uri(figs / name)

    blocks = []

    # -- Encoding vs retrieval --------------------------------------------
    ev = tables / "encVSret_summary.json"
    if ev.exists():
        s = json.loads(ev.read_text())
        cols = ["X", "Y", "Z", "Cluster Size (mm3)", "Anatomical Label"]
        eg = _read_csv(tables / "encVSret_encoding_gt_retrieval.csv")
        rg = _read_csv(tables / "encVSret_retrieval_gt_encoding.csv")
        cj = _read_csv(tables / "encVSret_conjunction.csv")
        gfig = _fig_block(uri("encVSret_glass.png"), _cap(
            "<b>Encoding vs. retrieval difference map.</b> Warm = greater "
            "convergence for encoding; cool = greater for retrieval. "
            "Voxelwise-thresholded — read directionally."))
        blocks.append(
            f'<h3 class="sub">Encoding vs. retrieval '
            f'<span class="muted" style="font-weight:400">'
            f'({s.get("n_encoding","—")} encoding vs {s.get("n_retrieval","—")} '
            f'retrieval experiments)</span></h3>'
            f'<p class="note">The classic memory dissociation (subsequent-memory '
            f'/ HERA). Where do the two phases diverge, and what core do they '
            f'share?</p>{gfig or ""}'
            f'<div class="grid2" style="margin-top:14px">'
            f'<div><div class="eyebrow">Encoding &gt; retrieval</div>'
            f'{_table_html(eg, cols=cols, max_rows=6)}</div>'
            f'<div><div class="eyebrow">Retrieval &gt; encoding</div>'
            f'{_table_html(rg, cols=cols, max_rows=6)}</div></div>'
            f'<div class="eyebrow" style="margin-top:14px">Shared memory core '
            f'(encoding ∧ retrieval)</div>{_table_html(cj, cols=cols, max_rows=6)}')

    # -- DMN overlap ------------------------------------------------------
    dj = tables / "dmn_overlap.json"
    if dj.exists():
        d = json.loads(dj.read_text())
        pct = int(round(100 * d.get("fraction_retrieval_in_dmn", 0)))
        fig = _fig_block(uri("dmn_overlap.png"), _cap(
            "Retrieval convergence (hot) with the <b>default-mode network</b> "
            "outlined in green (Yeo-2011). The retrieval network overlaps the "
            "DMN substantially but not completely — it also recruits control "
            "regions outside it."))
        blocks.append(
            f'<h3 class="sub">Overlap with the default-mode network</h3>'
            f'<div class="vcards"><div class="vcard"><div class="vbig">{pct}%</div>'
            f'<div class="vlab">of the retrieval map lies within the DMN '
            f'(Dice = {d.get("dice","—")})</div></div></div>{fig or ""}')

    # -- Landmark recovery ------------------------------------------------
    lm = _read_csv(tables / "landmark_recovery.csv")
    if lm is not None and len(lm):
        n_ok = int((lm["Recovered"] == "yes").sum())
        blocks.append(
            f'<h3 class="sub">Recovery of the canonical recollection network</h3>'
            f'<p class="note">Does the automated result recover each node of the '
            f'core recollection network described in the review literature '
            f'(Rugg &amp; Vilberg, 2013)? <b>{n_ok}/{len(lm)} nodes recovered.</b>'
            f'</p>{_table_html(lm)}')

    if not blocks:
        return ""
    return f"""
  <section class="card" id="extended">
    <div class="eyebrow"><span class="section-num">07</span>Extended analyses</div>
    <h2>Deeper tests of the memory network</h2>
    {"".join(blocks)}
  </section>"""


def _validation_section(cfg: Config) -> str:
    """Section for the sensitivity analysis, cross-database agreement, and the
    GingerALE/Sleuth export — the three checks that a convergent region is real,
    not an artefact of one database or a loose construct."""
    import json
    tables = cfg.path("tables")
    root = cfg.root
    summary = {}
    sj = tables / "validation_summary.json"
    if sj.exists():
        try:
            summary = json.loads(sj.read_text())
        except Exception:
            summary = {}

    cards = []
    sens = summary.get("sensitivity", {})
    if sens:
        pct = int(round(100 * sens.get("a_in_b", 0)))
        cards.append(
            f'<div class="vcard"><div class="vbig">{pct}%</div>'
            f'<div class="vlab">of clusters replicate under a stricter construct '
            f'(≥2 inclusion terms, n={sens.get("strict_n_experiments","—")} '
            f'experiments)</div></div>')
    cx = summary.get("cross_database", {})
    if cx:
        pa = int(round(100 * cx.get("a_in_b", 0)))
        cards.append(
            f'<div class="vcard"><div class="vbig">{pa}%</div>'
            f'<div class="vlab">of {cx.get("db_a","db A")} clusters have a match '
            f'in {cx.get("db_b","db B")} — two independently built databases '
            f'agree</div></div>')
    sleuth = root / "results" / "gingerale" / "episodic_retrieval_sleuth.txt"
    if sleuth.exists():
        cards.append(
            '<div class="vcard"><div class="vbig">✓</div><div class="vlab">'
            'GingerALE/Sleuth input exported — the analysis can be independently '
            'reproduced in the classic tool</div></div>')

    if not cards:
        return ""  # nothing computed yet

    sens_tab = _read_csv(tables / "sensitivity_clusters.csv")
    ns_tab = _read_csv(tables / "crossdb_neurosynth_clusters.csv")
    nq_tab = _read_csv(tables / "crossdb_neuroquery_clusters.csv")
    cols = ["X", "Y", "Z", "Cluster Size (mm3)", "Anatomical Label"]
    extra = ""
    if sens_tab is not None and len(sens_tab):
        extra += ('<div class="eyebrow" style="margin-top:18px">Stricter-construct '
                  'clusters</div>' + _table_html(sens_tab, cols=cols, max_rows=10))
    if ns_tab is not None or nq_tab is not None:
        extra += ('<div class="grid2" style="margin-top:16px">'
                  f'<div><div class="eyebrow">Neurosynth only</div>'
                  f'{_table_html(ns_tab, cols=cols, max_rows=8)}</div>'
                  f'<div><div class="eyebrow">NeuroQuery only</div>'
                  f'{_table_html(nq_tab, cols=cols, max_rows=8)}</div></div>')

    return f"""
  <section class="card" id="validation">
    <div class="eyebrow"><span class="section-num">08</span>Validation</div>
    <h2>Is the result real?</h2>
    <p class="note">Three independent checks that the convergent regions are not
      an artefact of one database or a loose search: a stricter construct, the
      agreement between two independently built databases, and an export that
      lets the whole analysis be reproduced in GingerALE.</p>
    <div class="vcards">{"".join(cards)}</div>
    {extra}
  </section>"""


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
_CSS = """
:root{
  --ground:#f5f7f9; --panel:#ffffff; --panel2:#fbfcfd; --ink:#141922; --muted:#5b6675;
  --line:#e4e8ee; --primary:#2f5d8a; --primary-soft:#e8eef5;
  --accent:#c76f28; --good:#2f7d55; --warn:#b7791f; --crit:#b23b3b;
  --good-bg:#e7f2ec; --warn-bg:#faf1dd; --crit-bg:#f7e6e6;
  --serif:ui-serif,Georgia,"Iowan Old Style","Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --radius:14px; --shadow:0 1px 2px rgba(20,25,34,.04),0 8px 24px rgba(20,25,34,.06);
}
@media (prefers-color-scheme:dark){:root{
  --ground:#0e1116; --panel:#161b22; --panel2:#12171e; --ink:#e6eaf0; --muted:#96a0ad;
  --line:#252c36; --primary:#7fb0dd; --primary-soft:#18222e; --accent:#e0955a;
  --good:#5fb98a; --warn:#d9ad5b; --crit:#e07a7a;
  --good-bg:#152318; --warn-bg:#241f14; --crit-bg:#24181a;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
:root[data-theme="light"]{
  --ground:#f5f7f9; --panel:#ffffff; --panel2:#fbfcfd; --ink:#141922; --muted:#5b6675;
  --line:#e4e8ee; --primary:#2f5d8a; --primary-soft:#e8eef5; --accent:#c76f28;
  --good:#2f7d55; --warn:#b7791f; --crit:#b23b3b;
  --good-bg:#e7f2ec; --warn-bg:#faf1dd; --crit-bg:#f7e6e6;}
:root[data-theme="dark"]{
  --ground:#0e1116; --panel:#161b22; --panel2:#12171e; --ink:#e6eaf0; --muted:#96a0ad;
  --line:#252c36; --primary:#7fb0dd; --primary-soft:#18222e; --accent:#e0955a;
  --good:#5fb98a; --warn:#d9ad5b; --crit:#e07a7a;
  --good-bg:#152318; --warn-bg:#241f14; --crit-bg:#24181a;}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 90px}
header.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--ground) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.top-inner{max-width:1080px;margin:0 auto;padding:14px 24px;display:flex;
  align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{font-family:var(--serif);font-weight:600;font-size:1.05rem}
.brand .dot{color:var(--accent)}
.eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);font-weight:600}
.hero{padding:56px 0 8px}
.hero h1{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,4.4vw,3.1rem);
  line-height:1.06;margin:.3em 0 .35em;text-wrap:balance;max-width:19ch}
.hero p.lede{font-size:1.14rem;color:var(--muted);max-width:62ch;margin:0}
.meta{margin-top:18px;font-size:.85rem;color:var(--muted)}
.chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:12px;margin:28px 0 8px}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:12px 16px;box-shadow:var(--shadow)}
.chip-value{display:block;font-family:var(--serif);font-size:1.45rem;font-weight:600;
  font-variant-numeric:tabular-nums;line-height:1.12}
.chip-label{display:block;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-top:4px}
section.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:28px 30px;margin-top:22px;box-shadow:var(--shadow)}
section.card h2{font-family:var(--serif);font-weight:600;font-size:1.5rem;margin:.1em 0}
h3.sub{font-family:var(--serif);font-weight:600;font-size:1.15rem;margin:26px 0 2px;
  padding-top:18px;border-top:1px solid var(--line)}
h3.sub:first-of-type{border-top:0;padding-top:6px}
.section-num{color:var(--accent);font-variant-numeric:tabular-nums;margin-right:.5ch}
.card p.note{color:var(--muted);font-size:.94rem;max-width:70ch}
.cap{font-size:.86rem;color:var(--muted);margin:10px 2px 0;line-height:1.5}
.cap b{color:var(--ink);font-weight:600}
.figblock{margin:0}
.figblock img{width:100%;height:auto;border-radius:10px;border:1px solid var(--line);
  background:#fff;display:block}
.viewer-frame{width:100%;height:540px;border:1px solid var(--line);border-radius:10px;
  background:#fff;display:block}
.prisma-wide{max-width:760px;margin:8px auto 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}
@media (max-width:760px){.grid2{grid-template-columns:1fr}}
.table-wrap{overflow-x:auto;margin-top:14px;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:.88rem}
thead th{background:var(--primary-soft);color:var(--ink);text-align:left;
  padding:9px 12px;font-weight:600;white-space:nowrap}
tbody td{padding:8px 12px;border-top:1px solid var(--line);font-variant-numeric:tabular-nums}
tbody tr:hover{background:color-mix(in srgb,var(--primary-soft) 50%,transparent)}
td.num{text-align:right}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.74rem;font-weight:600}
.pill-good{background:var(--good-bg);color:var(--good)}
.pill-warn{background:var(--warn-bg);color:var(--warn)}
.pill-crit{background:var(--crit-bg);color:var(--crit)}
.muted{color:var(--muted)}
.terms{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.term{background:var(--primary-soft);color:var(--primary);border-radius:8px;
  padding:4px 10px;font-size:.82rem;font-weight:600}
.tabs{margin-top:16px}
.tabbar{display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--line);
  padding-bottom:2px;margin-bottom:16px}
.tab{appearance:none;border:1px solid transparent;background:transparent;color:var(--muted);
  font-family:var(--sans);font-size:.86rem;font-weight:600;padding:8px 14px;border-radius:9px 9px 0 0;
  cursor:pointer}
.tab:hover{color:var(--ink);background:var(--panel2)}
.tab.active{color:var(--primary);background:var(--primary-soft);
  border-color:var(--line);border-bottom-color:transparent}
.tabpanel{display:none}
.tabpanel.active{display:block;animation:fade .25s ease}
.loadbtn{appearance:none;cursor:pointer;font-family:var(--sans);font-weight:600;
  font-size:.9rem;color:#fff;background:var(--primary);border:0;border-radius:10px;
  padding:12px 20px;box-shadow:var(--shadow)}
.loadbtn:hover{filter:brightness(1.06)}
.lazy-slot{margin-top:12px}
@keyframes fade{from{opacity:0}to{opacity:1}}
.vcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px;margin-top:16px}
.vcard{background:var(--panel2);border:1px solid var(--line);border-radius:12px;
  padding:18px 20px}
.vbig{font-family:var(--serif);font-size:2rem;font-weight:600;color:var(--good);
  font-variant-numeric:tabular-nums;line-height:1}
.vlab{font-size:.86rem;color:var(--muted);margin-top:8px;line-height:1.45}
ul.lim{margin:8px 0 0;padding-left:1.1em;color:var(--muted)}
ul.lim li{margin:6px 0}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.toc a{font-size:.82rem;text-decoration:none;color:var(--primary);
  background:var(--primary-soft);padding:5px 11px;border-radius:8px}
footer.foot{margin-top:36px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--muted);font-size:.85rem}
a{color:var(--primary)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;scroll-behavior:auto}}
"""

_JS = """
document.querySelectorAll('.tab').forEach(function(btn){
  btn.addEventListener('click',function(){
    var g=btn.dataset.g,i=btn.dataset.i;
    document.querySelectorAll('.tab[data-g="'+g+'"]').forEach(function(b){b.classList.remove('active');});
    document.querySelectorAll('.tabpanel[data-g="'+g+'"]').forEach(function(p){p.classList.remove('active');});
    btn.classList.add('active');
    document.querySelector('.tabpanel[data-g="'+g+'"][data-i="'+i+'"]').classList.add('active');
  });
});
document.querySelectorAll('.loadbtn').forEach(function(btn){
  btn.addEventListener('click',function(){
    var t=document.getElementById(btn.dataset.tpl);
    document.getElementById(btn.dataset.tpl+'-slot').innerHTML=t.innerHTML;
    btn.style.display='none';
  });
});
"""


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build_dashboard(cfg: Config) -> Path:
    figs = cfg.path("figures")
    tables = cfg.path("tables")
    a_ale = cfg["ale"]

    prisma = _read_csv(tables / "prisma_counts.csv")
    clusters = _read_csv(tables / "ale_clusters_labelled.csv")
    if clusters is None:
        clusters = _read_csv(tables / "ale_significant_clusters.csv")
    decoding = _read_csv(tables / "functional_decoding.csv")
    diag_summary = _diagnostics_summary(tables)

    n_db = int((prisma["source"] != "ALL").sum()) if prisma is not None else 0
    n_clusters = len(clusters) if clusters is not None else 0
    top_region = (clusters.iloc[0]["Anatomical Label"]
                  if clusters is not None and len(clusters)
                  and "Anatomical Label" in clusters.columns else "—")
    top_term = (decoding.iloc[0]["term"]
                if decoding is not None and len(decoding) else "—")

    merged_n = "—"
    rep = cfg.path("results") / "REPORT.md"
    if rep.exists():
        for line in rep.read_text().splitlines():
            if "Final included experiments" in line:
                d = "".join(ch for ch in line.split(":")[-1] if ch.isdigit())
                if d:
                    merged_n = d
                break

    chips = "".join([
        _chip("experiments", str(merged_n)),
        _chip("databases", str(n_db)),
        _chip("convergent clusters", str(n_clusters)),
        _chip("strongest region", str(top_region)),
        _chip("top decoded term", str(top_term)),
    ])

    def fb(name, cap):  # figure block from a png filename
        return _fig_block(_img_uri(figs / name), _cap(cap))

    # ---- Section 2: convergence gallery (tabs) ----------------------------
    conv_tabs = _tabs([
        ("Glass brain", fb("ale_glass_brain.png",
            "A <b>see-through projection</b> of the whole brain from three angles; "
            "brighter regions are where more independent studies converge. Best "
            "for seeing every cluster at once.")),
        ("Slices", fb("ale_slices.png",
            "The same result <b>sliced through the standard MNI brain</b> at the "
            "peak — shows depth and left/right position.")),
        ("Surface", fb("ale_surface.png",
            "Convergence painted onto an <b>inflated cortical surface</b> (sulci "
            "unfolded), so activation buried inside folds is visible. Lateral and "
            "medial views of both hemispheres.")),
        ("Axial montage", fb("ale_montage.png",
            "A <b>ladder of axial slices</b> from the bottom to the top of the "
            "brain — shows how far each cluster extends vertically.")),
        ("Interactive volume", _iframe_block(figs / "ale_interactive.html", _cap(
            "<b>Drag the crosshair</b> through the brain to explore the map and "
            "read exact MNI coordinates. Fully interactive."))),
        ("3-D surface", _lazy_viewer_block(
            figs / "ale_surface_interactive.html",
            _cap("A fully <b>rotatable 3-D cortical surface</b>. Spin it, zoom, "
                 "and see convergence on the folded cortex. Loads on demand."),
            "▶ Load the rotatable 3-D surface viewer")),
    ])

    # ---- Section 3: decoding ---------------------------------------------
    term_chips = ""
    if decoding is not None and len(decoding):
        term_chips = '<div class="terms">' + "".join(
            f'<span class="term">{html.escape(str(t))}</span>'
            for t in decoding["term"].head(14)) + "</div>"

    # ---- Section 4: diagnostics gallery ----------------------------------
    diag_tabs = _tabs([
        ("Robustness", fb("diag_robustness.png",
            "Bar length = <b>independent experiments</b> supporting each cluster; "
            "colour = whether any <b>single study</b> could overturn it "
            "(green robust → red fragile).")),
        ("File-drawer", fb("diag_file_drawer.png",
            "We inject <b>fake null studies</b> (the 'file drawer' of unpublished "
            "results) and re-run. A nearly flat line means the result survives "
            "publication bias.")),
        ("Jackknife heatmap", fb("diag_jackknife_heatmap.png",
            "Each row is a study, each column a cluster; brightness = <b>how much "
            "that study drives that cluster</b>. No single bright row = no "
            "over-reliance on one study.")),
    ])

    # ---- Section 5: MACM gallery -----------------------------------------
    macm_tabs = _tabs([
        ("Glass brain", fb("macm_glass_brain.png",
            "Regions that <b>co-activate</b> with the strongest retrieval hub "
            "across the whole database — a meta-analytic estimate of its "
            "functional network.")),
        ("Axial montage", fb("macm_montage.png",
            "Axial slices of the coactivation network.")),
        ("Interactive", _iframe_block(figs / "macm_interactive.html", _cap(
            "<b>Explore the coactivation network</b> — drag the crosshair "
            "through the brain."))),
    ])

    # ---- Section 6: contrast ---------------------------------------------
    a_name = cfg["contrast"]["group_a"]["name"]
    b_name = cfg["contrast"]["group_b"]["name"]
    ctab_a = _read_csv(tables / f"contrast_{a_name}_gt_{b_name}.csv")
    ctab_b = _read_csv(tables / f"contrast_{b_name}_gt_{a_name}.csv")
    conj = _read_csv(tables / f"conjunction_{a_name}_AND_{b_name}.csv")
    ccols = ["X", "Y", "Z", "Cluster Size (mm3)", "Anatomical Label"]
    contrast_tabs = _tabs([
        ("Difference map", fb("contrast_subtraction_glass.png",
            f"<b>Where the two differ.</b> Warm = more convergence for "
            f"{a_name}; cool = more for {b_name}. Voxelwise-thresholded — read "
            f"directionally, not as corrected clusters.")),
        ("Shared core", fb("contrast_conjunction_glass.png",
            f"<b>Where both converge</b> — the retrieval core common to "
            f"{a_name} and {b_name} (minimum-statistic conjunction).")),
    ])

    # limitations parsed from REPORT.md section 7
    lims = []
    if rep.exists():
        grab = False
        for line in rep.read_text().splitlines():
            if line.startswith("## 7"):
                grab = True
                continue
            if grab and line.startswith("## "):
                break
            if grab and line.strip().startswith("- "):
                lims.append(line.strip()[2:])
    lim_html = ("<ul class='lim'>" + "".join(
        f"<li>{html.escape(x)}</li>" for x in lims) + "</ul>") if lims else \
        '<p class="muted">See REPORT.md.</p>'

    # Prefer a hand-designed PRISMA image at assets/prisma_flow.png if present
    # (persists across pipeline re-runs, which regenerate figures/prisma_flow.png).
    custom_prisma = cfg.root / "assets" / "prisma_flow.png"
    prisma_src = custom_prisma if custom_prisma.exists() else (figs / "prisma_flow.png")
    prisma_fig = _fig_block(_img_uri(prisma_src), _cap(
        "Read <b>top → bottom</b>: every study identified in the databases, "
        "narrowed by cognitive-term screening and a minimum-foci check to the "
        "final pool. Red boxes are exclusions, with the reason and count."))
    prisma_fig = (f'<div class="prisma-wide">{prisma_fig}</div>'
                  if prisma_fig else "")

    decode_fig = fb("decoding_terms.png",
        "Each bar is a cognitive term; length = <b>how strongly the region is "
        "associated with it</b> across ~14,000 studies. Memory/retrieval terms "
        "on top independently validate the region's function.")

    n_iters = a_ale["n_iters"]
    body = f"""
<header class="top"><div class="top-inner">
  <span class="brand">Episodic Retrieval <span class="dot">·</span> ALE Meta-Analysis</span>
  <span class="eyebrow">NiMARE · Neurosynth + NeuroQuery</span>
</div></header>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">Coordinate-based meta-analysis</div>
    <h1>Where the brain converges during episodic memory retrieval</h1>
    <p class="lede">A reproducible synthesis of the published fMRI literature —
      pulled from multiple public coordinate databases, pooled with Activation
      Likelihood Estimation, stress-tested for robustness, and mapped from every
      angle.</p>
    <div class="meta">Generated {date.today().isoformat()} ·
      owner {html.escape(cfg['project']['owner'])} ·
      cluster-level FWE p&lt;{a_ale['fwe_cluster_p']}, {n_iters} permutations</div>
    <div class="chips">{chips}</div>
    <nav class="toc">
      <a href="#prisma">Selection</a><a href="#convergence">Convergence</a>
      <a href="#decoding">Decoding</a><a href="#robustness">Robustness</a>
      <a href="#macm">Network</a><a href="#contrast">Dual-process</a>
      <a href="#extended">Extended</a><a href="#validation">Validation</a>
    </nav>
  </div>

  <section class="card" id="prisma">
    <div class="eyebrow"><span class="section-num">01</span>Study selection</div>
    <h2>PRISMA &amp; provenance</h2>
    <p class="note">Studies were drawn from {n_db} public database(s) and screened
      by cognitive term against the construct — a reproducible analogue of a
      systematic search.</p>
    {prisma_fig}
    <div style="margin-top:18px">{_table_html(prisma)}</div>
  </section>

  <section class="card" id="convergence">
    <div class="eyebrow"><span class="section-num">02</span>Convergence</div>
    <h2>Where activation reliably converges</h2>
    <p class="note">ALE with cluster-level family-wise-error correction, viewed
      five ways. Peaks are labelled with the Harvard-Oxford atlas.</p>
    {conv_tabs}
    <div style="margin-top:8px">{_table_html(clusters, cols=['Cluster ID','X','Y','Z','Peak Stat','Cluster Size (mm3)','Anatomical Label'])}</div>
  </section>

  <section class="card" id="decoding">
    <div class="eyebrow"><span class="section-num">03</span>Reverse inference</div>
    <h2>What the region is “about”</h2>
    <p class="note">Functional decoding asks the database the inverse question:
      given this region, which cognitive terms is it most associated with?</p>
    <div class="grid2">{decode_fig or ''}<div>{term_chips}</div></div>
  </section>

  <section class="card" id="robustness">
    <div class="eyebrow"><span class="section-num">04</span>Robustness</div>
    <h2>How much to trust each cluster</h2>
    <p class="note">Three independent stress tests: how broadly each cluster is
      supported, whether any single study drives it, and whether it survives the
      file-drawer problem.</p>
    {diag_tabs}
    <div style="margin-top:8px">{_diagnostics_table_html(diag_summary)}</div>
  </section>

  <section class="card" id="macm">
    <div class="eyebrow"><span class="section-num">05</span>Connectivity</div>
    <h2>The region’s coactivation network (MACM)</h2>
    <p class="note">Studies across the whole database that coactivate with the
      strongest retrieval hub — a meta-analytic estimate of its functional network.</p>
    {macm_tabs}
  </section>

  <section class="card" id="contrast">
    <div class="eyebrow"><span class="section-num">06</span>Dual-process</div>
    <h2>Recognition vs. recall</h2>
    <p class="note">Splitting retrieval into recognition/familiarity vs.
      recall/autobiographical tests dual-process theory: where the two diverge,
      and the core they share.</p>
    {contrast_tabs}
    <div class="grid2" style="margin-top:16px">
      <div><div class="eyebrow">{html.escape(a_name)} &gt; {html.escape(b_name)}</div>
        {_table_html(ctab_a, cols=ccols, max_rows=8)}</div>
      <div><div class="eyebrow">{html.escape(b_name)} &gt; {html.escape(a_name)}</div>
        {_table_html(ctab_b, cols=ccols, max_rows=8)}</div>
    </div>
    <div class="eyebrow" style="margin-top:18px">Shared retrieval core (conjunction)</div>
    {_table_html(conj, cols=ccols)}
  </section>
{_advanced_section(cfg)}
{_validation_section(cfg)}
  <section class="card">
    <div class="eyebrow"><span class="section-num">09</span>Caveats</div>
    <h2>Limitations</h2>
    {lim_html}
  </section>

  <footer class="foot">
    Built with NiMARE · data from Neurosynth &amp; NeuroQuery · fully reproducible
    from <code>config/config.yaml</code>. An automated, high-throughput synthesis —
    a complement to, not a replacement for, a hand-screened systematic review.
  </footer>
</div>
<script>{_JS}</script>
"""
    out = cfg.path("results") / "dashboard.html"
    page = (f"<title>Episodic Retrieval — ALE Meta-Analysis</title>\n"
            f"<style>{_CSS}</style>\n{body}")
    out.write_text(page)
    logger.info("Wrote dashboard to %s", out)
    return out
