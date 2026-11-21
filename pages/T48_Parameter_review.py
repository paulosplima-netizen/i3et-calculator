"""T48 · Parameter review — the expert-block parameters with the periodic literature review.

Query only. Ranges, recommendations, sources, alerts and notes come from the reference base
(P30, P64–P68). The "Adopted in …" column follows the open project: its values are the
workbook catalogue (the Excel model) overlaid with what the user changed in that project's
analysis (D08); edited values are marked and show the workbook value struck through. With no
project open, it shows the Excel model itself. Nothing is editable here and a suggested value
never reaches the calculation — to change a value of an analysis, open Selected Parameters
(T04). The workbook prevails and the reference base is immutable.
New screen: it replaces the "I3et Parametros Expert" artifact and has no revised prototype.
"""

from __future__ import annotations

import html
import re
import sqlite3
from contextlib import closing

import streamlit as st

from core import param_review as pr
from core import project as project_core
from ui import flow, navigation, state

flow.begin("Parameter review", needs_project=False)

ACTION_LABEL = {"keep": "Keep", "adjust": "Adjust", "verify": "Verify"}
ACTION_COLOR = {"keep": ("#e6f4ea", "#1e6b34"), "adjust": ("#fff4e0", "#9a5b00"),
                "verify": ("#e8f0fe", "#1a4db3")}
SEV_COLOR = {"high": "#c0392b", "medium": "#d98a00", "low": "#6b7280"}
TAG_LABEL = {"bat": "Battery", "ice": "Combustion engine"}
FILTERS = ["All", "Batteries", "Combustion engines", "With recommendation"]
CHANGED = 1e-12
MASTER_NAME = "Excel Model LCA_LV_i3ET_20261119"
BLOCK_TITLE = pr.BLOCK_NAMES


def _e(texto) -> str:
    return html.escape("" if texto is None else str(texto))


def _rich(texto: str) -> str:
    """Texto escapado com **negrito** e `codigo` simples."""
    t = _e(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


def _open_t04(idcp: str) -> None:
    st.session_state["t04_prefill"] = idcp
    st.switch_page(navigation.SCREENS["T04"][0])


def _cell(now, base, unit, dec) -> str:
    """Valor atual; se o da data-base for diferente, vem riscado antes."""
    atual = pr.fmt(now, unit, dec)
    if base is not None and now is not None and abs(base - now) > CHANGED:
        return f"<s style='color:#9ca3af'>{_e(pr.fmt(base, unit, dec))}</s> {_e(atual)}"
    return _e(atual)


def _bar(r: pr.PanelRow) -> str:
    if r.lo is None or r.hi is None or r.value is None or r.hi <= r.lo:
        return ""
    pos = min(100.0, max(0.0, (r.value - r.lo) / (r.hi - r.lo) * 100))
    cor = "#c0392b" if not r.lo <= r.value <= r.hi else "#2f6fdb"
    return ("<div style='position:relative;height:4px;background:#e5e7eb;border-radius:2px;"
            "margin-top:4px'><div style='position:absolute;top:-2px;width:3px;height:8px;"
            f"background:{cor};left:{pos:.1f}%'></div></div>")


def _recommendation(r: pr.PanelRow, dec) -> str:
    rev = r.revision
    bg, fg = ACTION_COLOR[rev.action]
    out = [f"<span style='background:{bg};color:{fg};padding:1px 8px;border-radius:10px;"
           f"font-size:12px;font-weight:600'>{ACTION_LABEL[rev.action]}</span>"]
    if rev.field:
        campo = pr.FIELD_LABEL[rev.field]
        if rev.suggested is not None:
            de = "" if rev.from_value is None else (
                f"<s style='color:#9ca3af'>{_e(pr.fmt(rev.from_value, r.unit, dec))}</s> → ")
            deriv = " (derived)" if rev.action == "verify" else ""
            out.append(f"<div style='font-size:12px'>{_e(campo)}: {de}"
                       f"<b>{_e(pr.fmt(rev.suggested, r.unit, dec))}</b>{deriv}</div>")
        elif rev.action == "verify":
            out.append(f"<div style='font-size:12px'>{_e(campo)}: check in the workbook — "
                       "no suggested value</div>")
    if rev.rationale:
        out.append(f"<div style='font-size:12px;color:#4b5563'>{_e(rev.rationale)}</div>")
    if rev.caveat:
        out.append(f"<div style='font-size:12px;color:#9a5b00'>⚠ {_e(rev.caveat)}</div>")
    if rev.accepted:
        out.append("<div style='font-size:12px;color:#1e6b34'>✓ accepted"
                   f" · saved on {_e(rev.accepted_date)}</div>")
    return "".join(out)


def _row_html(r: pr.PanelRow, dec) -> str:
    rev = r.revision
    tag = (f" <span style='font-size:11px;background:#f3f4f6;border-radius:8px;"
           f"padding:0 6px'>{_e(TAG_LABEL[rev.tag])}</span>") if rev.tag else ""
    adotado = r.text if (r.value is None and r.text) else None
    if r.source == "User":
        antes = _e(r.text if r.default is None else pr.fmt(r.default, r.unit, dec))
        agora = _e(adotado) if adotado else _e(pr.fmt(r.value, r.unit, dec))
        cel_val = (f"<s style='color:#9ca3af'>{antes}</s> <b>{agora}</b>"
                   "<div style='font-size:11px;color:#9a5b00'>edited in this project</div>")
    else:
        cel_val = _e(adotado) if adotado else _cell(r.value, rev.baseline_value, r.unit, dec)
    fontes = "<br>".join(_e(ref) + (f" ({_e(y)})" if y else "") for ref, y in rev.sources)
    nota = f"<div style='font-size:11px;color:#6b7280'>{_e(r.note)}</div>" if r.note else ""
    avisos = "".join(f"<div style='font-size:11px;color:#c0392b'>⚠ {_e(f)}</div>"
                     for f in r.flags)
    td = "style='padding:6px 8px;border-top:1px solid #e5e7eb;vertical-align:top"
    return (
        f"<tr><td {td};color:#6b7280'>{rev.panel_no}</td>"
        f"<td {td}'><b>{_e(r.name)}</b>{tag}<div style='font-size:11px;color:#6b7280'>"
        f"{_e(r.unit or '(no unit)')} · {_e(r.idcp)}</div>{nota}{avisos}</td>"
        f"<td {td};text-align:right'>{_cell(r.lo, rev.baseline_min, r.unit, dec)}</td>"
        f"<td {td};text-align:right'>{_cell(r.mf, rev.baseline_mf, r.unit, dec)}</td>"
        f"<td {td};text-align:right'>{_cell(r.hi, rev.baseline_max, r.unit, dec)}</td>"
        f"<td {td};text-align:right'>{cel_val}{_bar(r)}</td>"
        f"<td {td};min-width:260px'>{_recommendation(r, dec)}</td>"
        f"<td {td};font-size:11px;color:#4b5563'>{fontes}</td></tr>")


def _table_html(grupo: list[pr.PanelRow], dec, adopted_title: str) -> str:
    th = "style='text-align:left;padding:6px 8px;font-size:12px;color:#4b5563'"
    head = ("<tr>" + "".join(f"<th {th}>{c}</th>" for c in (
        "#", "Parameter", "Min.", "Most freq.", "Max.", _e(adopted_title), "Recommendation",
        "Sources")) + "</tr>")
    return ("<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%;"
            f"font-size:13px'>{head}{''.join(_row_html(r, dec) for r in grupo)}</table></div>")


def _alert_html(a: pr.Alert) -> str:
    cor = SEV_COLOR.get(a.severity, "#6b7280")
    nos = ", ".join(f"#{n}" for n in a.panel_nos)
    partes = [f"<div style='border-left:4px solid {cor};padding:6px 12px;margin:8px 0;"
              "background:#fafafa'>",
              f"<div style='font-size:11px;font-weight:700;color:{cor}'>"
              f"{_e(a.severity.upper())}</div><div><b>{_e(a.title)}</b></div>"]
    if a.context:
        partes.append(f"<div style='font-size:12px;color:#6b7280'>{_e(a.context)}</div>")
    if a.reported or a.adopted:
        partes.append("<div style='font-size:12px'>Reported: "
                      f"<b>{_e(a.reported)}</b> · Adopted: <b>{_e(a.adopted)}</b></div>")
    if a.body:
        partes.append(f"<div style='font-size:12px'>{_e(a.body)}</div>")
    if nos:
        partes.append(f"<div style='font-size:12px;color:#6b7280'>Parameters: {_e(nos)}</div>")
    if a.url and a.url.startswith(("http://", "https://")):
        partes.append(f"<div style='font-size:12px'><a href='{_e(a.url)}' target='_blank' "
                      "rel='noopener noreferrer'>Source</a></div>")
    partes.append("</div>")
    return "".join(partes)


# Consulta independente de projeto: tudo vem da base de referencia (P30, P64–P68).
with closing(sqlite3.connect(f"file:{state.REFERENCE_DB}?mode=ro", uri=True)) as conn:
    adopted_title, adopted_note, overrides = f"Adopted in {MASTER_NAME}", None, None
    ppath = state.project_path()
    if ppath and flow.selected_count() == 1:
        try:
            with closing(sqlite3.connect(f"file:{ppath}?mode=ro", uri=True)) as pconn:
                ident = project_core.identity(pconn)
                ida = flow.current_ida(pconn)
                if ident and ida is not None:
                    prof = pconn.execute("SELECT ParamProfile FROM D06_Analysis WHERE IDA = ?",
                                         (ida,)).fetchone()[0]
                    overrides = pr.user_overrides(pconn, ida, prof)
                    adopted_title = f"Adopted in {ident['ProjectName']}"
                    adopted_note = (f"Adopted values: project {ident['ProjectName']} · analysis "
                                    f"A{ida} · depth {prof} · {len(overrides)} edited.")
        except sqlite3.Error:
            overrides = None
    try:
        rows = pr.panel_rows(conn, overrides=overrides)
    except sqlite3.Error:
        rows = []
    if not rows:
        st.info("The reference base has no parameter review loaded.")
        st.stop()
    try:
        news = pr.alerts(conn)
        notes = pr.review_texts(conn, "note")
        hist = pr.review_texts(conn, "history")
    except sqlite3.Error:
        news, notes, hist = [], [], []

    summary = pr.summary(rows)
    st.caption(
        f"Baseline {summary['review_date']} · adopted values and ranges are those of the "
        "workbook catalogue; suggestions do not change any calculation. "
        "The workbook prevails.")
    if adopted_note:
        st.caption(adopted_note)
    else:
        st.caption("No project open: adopted values are those of the Excel model.")
    k = st.columns(6)
    k[0].metric("Parameters", summary["total"])
    k[1].metric("Battery", summary["battery"])
    k[2].metric("Combustion engines", summary["ice"])
    k[3].metric("Distinct sources", summary["sources"])
    k[4].metric("Alerts", len(news))
    k[5].metric("Adjustments", summary["adjustments"])

    if news:
        with st.expander(f"New developments ({len(news)} · baseline {summary['review_date']})"):
            st.markdown("".join(_alert_html(a) for a in news), unsafe_allow_html=True)

    f1, f2, f3 = st.columns([3, 2, 3])
    term = f1.text_input("Search", placeholder="#, name, unit, block or source").strip()
    blocks = f2.multiselect("Block", [b for b in pr.BLOCKS if any(r.section == b for r in rows)],
                            format_func=lambda b: f"{b} — {BLOCK_TITLE.get(b, '')}")
    chip = f3.radio("Filter", FILTERS, horizontal=True, key="review_filter")

    def _shown(r: pr.PanelRow) -> bool:
        if not pr.matches(r, term):
            return False
        if blocks and r.section not in blocks:
            return False
        return {"All": True, "Batteries": r.revision.tag == "bat",
                "Combustion engines": r.revision.tag == "ice",
                "With recommendation": r.revision.action in ("adjust", "verify")}[chip]

    shown = [r for r in rows if _shown(r)]
    st.caption(f"{len(shown)} of {len(rows)} shown")

    dec = pr.family_decimals(rows)           # casas por familia de unidade, sobre o conjunto todo
    for bloco in pr.BLOCKS:
        grupo = [r for r in shown if r.section == bloco]
        if not grupo:
            continue
        st.markdown(f"#### {bloco} — {BLOCK_TITLE.get(bloco, '')}")
        st.markdown(_table_html(grupo, dec, adopted_title), unsafe_allow_html=True)

    if notes:
        st.subheader("Reading notes")
        st.markdown("".join(f"<p style='font-size:13px'>{_rich(t)}</p>" for _, t in notes),
                    unsafe_allow_html=True)
    if hist:
        st.subheader("Revision history")
        st.markdown("".join(f"<p style='font-size:13px'>{_rich(t)}</p>" for _, t in hist),
                    unsafe_allow_html=True)

    if not shown:
        st.stop()
    st.subheader("Parameter detail")
    labels = {r.idcp: f"#{r.revision.panel_no} · {r.idcp} · {r.name}" for r in shown}
    pick = st.selectbox("Parameter", list(labels), format_func=labels.get, key="review_pick")
    r = next(x for x in shown if x.idcp == pick)
    for flag in r.flags:
        st.warning(flag)
    past = pr.history(conn, r.idcp)[1:]
    if past:
        st.markdown("**Earlier reviews**")
        for h in past:
            st.write(f"- {h.review_date}: {ACTION_LABEL[h.action]}")
    if r.level == "X":
        st.caption("This is an Expanded-depth parameter: set the depth to Expanded in "
                   "Selected Parameters to edit it.")
    if st.button("Open in Selected Parameters", key="open_t04"):
        _open_t04(r.idcp)
