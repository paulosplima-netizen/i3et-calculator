"""Inline SVG charts for the exported report.

Two forms, chosen for the two questions the report answers: how much each
vehicle emits (magnitude, one series) and where those emissions come from
(composition, several series). Both are horizontal bars, because the category
labels are words and words read better along the vertical axis.

Everything here is a string. No plotting library, no image file, no external
request: the report has to open from a pen drive in ten years and still look
like itself. Colours arrive as CSS custom properties defined once in the
report's stylesheet, so light and dark swap in one place and the marks are
written against roles rather than hexes.

The palette is the validated default of the data-viz reference: eight
categorical hues in fixed order, never cycled. A ninth category does not get a
new hue -- it folds into "Outros".
"""

from __future__ import annotations

import html
import math

#: Categorical slots, in the fixed order that keeps adjacent pairs separable
#: for colour-vision deficiency. Never reordered, never cycled.
SERIES_SLOTS = 7
#: Anything past the slots, in the chrome's muted ink.
OTHER_ROLE = "var(--chart-other)"

BAR_HEIGHT = 18
BAR_GAP = 10
LABEL_WIDTH = 118
VALUE_WIDTH = 96
PAD_TOP = 26
PAD_BOTTOM = 26
WIDTH = 760
RADIUS = 4
#: Documento de referencia: 2px de superficie entre segmentos vizinhos.
SEGMENT_GAP = 2


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _fmt(v: float, casas: int = 0) -> str:
    """Brazilian number formatting, which is what the report is written in."""
    s = f"{v:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _nice_ticks(maximo: float, alvo: int = 5) -> list[float]:
    if maximo <= 0:
        return [0.0]
    bruto = maximo / alvo
    magnitude = 10 ** math.floor(math.log10(bruto))
    for passo in (1, 2, 2.5, 5, 10):
        if bruto <= passo * magnitude:
            passo = passo * magnitude
            break
    ticks, t = [], 0.0
    while t <= maximo * 1.0001:
        ticks.append(round(t, 10))
        t += passo
    if ticks[-1] < maximo:
        ticks.append(round(ticks[-1] + passo, 10))
    return ticks


def _rounded_right(x: float, y: float, w: float, h: float, r: float) -> str:
    """A bar anchored to the baseline: square at the axis, rounded at the value."""
    r = max(0.0, min(r, w, h / 2))
    if w <= 0:
        return ""
    return (f"M{x:.2f},{y:.2f} H{x + w - r:.2f} "
            f"A{r:.2f},{r:.2f} 0 0 1 {x + w:.2f},{y + r:.2f} "
            f"V{y + h - r:.2f} "
            f"A{r:.2f},{r:.2f} 0 0 1 {x + w - r:.2f},{y + h:.2f} "
            f"H{x:.2f} Z")


def _grid(escala, ticks, altura_plot, x0) -> str:
    partes = []
    for t in ticks:
        x = x0 + escala(t)
        partes.append(f'<line class="grid" x1="{x:.2f}" y1="{PAD_TOP - 8:.2f}" '
                      f'x2="{x:.2f}" y2="{PAD_TOP + altura_plot:.2f}"/>')
        partes.append(f'<text class="tick" x="{x:.2f}" y="{PAD_TOP - 12:.2f}" '
                      f'text-anchor="middle">{_esc(_fmt(t))}</text>')
    return "".join(partes)


def bar_chart(rows: list[tuple[str, float]], *, unidade: str,
              titulo: str = "", casas: int = 0) -> str:
    """One series, direct-labelled. No legend: the title names the series."""
    if not rows:
        return ""
    maximo = max(v for _, v in rows) or 1.0
    ticks = _nice_ticks(maximo)
    largura_plot = WIDTH - LABEL_WIDTH - VALUE_WIDTH
    escala = lambda v: largura_plot * v / ticks[-1]          # noqa: E731
    altura_plot = len(rows) * (BAR_HEIGHT + BAR_GAP)
    altura = PAD_TOP + altura_plot + PAD_BOTTOM

    partes = [_grid(escala, ticks, altura_plot, LABEL_WIDTH)]
    for i, (rotulo, valor) in enumerate(rows):
        y = PAD_TOP + i * (BAR_HEIGHT + BAR_GAP)
        w = escala(valor)
        partes.append(
            f'<g class="mark">'
            f'<title>{_esc(rotulo)}: {_esc(_fmt(valor, casas))} {_esc(unidade)}</title>'
            f'<text class="rotulo" x="{LABEL_WIDTH - 10}" y="{y + BAR_HEIGHT * 0.72:.2f}" '
            f'text-anchor="end">{_esc(rotulo)}</text>'
            f'<path class="barra" d="{_rounded_right(LABEL_WIDTH, y, w, BAR_HEIGHT, RADIUS)}"/>'
            f'<text class="valor" x="{LABEL_WIDTH + w + 8:.2f}" '
            f'y="{y + BAR_HEIGHT * 0.72:.2f}">{_esc(_fmt(valor, casas))}</text>'
            f'</g>')
    partes.append(f'<line class="eixo" x1="{LABEL_WIDTH}" y1="{PAD_TOP}" '
                  f'x2="{LABEL_WIDTH}" y2="{PAD_TOP + altura_plot}"/>')
    partes.append(f'<text class="unidade" x="{LABEL_WIDTH}" y="{altura - 8}">'
                  f'{_esc(unidade)}</text>')
    return _svg(partes, altura, titulo)


def stacked_bar_chart(rows: list[tuple[str, dict]], series: list[str], *,
                      unidade: str, titulo: str = "", casas: int = 0) -> str:
    """Composition. Legend always present; hover gives the value of a segment.

    `series` is the drawing order and the legend order at once, so the colour a
    reader learns in the legend is the colour they find in every bar.
    """
    if not rows or not series:
        return ""
    totais = [sum(v.get(s, 0.0) for s in series) for _, v in rows]
    maximo = max(totais) or 1.0
    ticks = _nice_ticks(maximo)
    largura_plot = WIDTH - LABEL_WIDTH - VALUE_WIDTH
    escala = lambda v: largura_plot * v / ticks[-1]          # noqa: E731
    altura_plot = len(rows) * (BAR_HEIGHT + BAR_GAP)
    altura = PAD_TOP + altura_plot + PAD_BOTTOM + 30

    partes = [_grid(escala, ticks, altura_plot, LABEL_WIDTH)]
    for i, (rotulo, valores) in enumerate(rows):
        y = PAD_TOP + i * (BAR_HEIGHT + BAR_GAP)
        x = float(LABEL_WIDTH)
        visiveis = [(s, float(valores.get(s, 0.0))) for s in series]
        visiveis = [(s, v) for s, v in visiveis if v > 0]
        for j, (s, v) in enumerate(visiveis):
            w = escala(v)
            ultimo = j == len(visiveis) - 1
            # 2px de superficie entre segmentos: o vizinho da direita cede o
            # espaco, de modo que a soma das larguras continua sendo o total.
            wd = w if ultimo else max(w - SEGMENT_GAP, 0.5)
            d = (_rounded_right(x, y, wd, BAR_HEIGHT, RADIUS) if ultimo
                 else f'M{x:.2f},{y:.2f} h{wd:.2f} v{BAR_HEIGHT} h-{wd:.2f} Z')
            partes.append(
                f'<g class="mark">'
                f'<title>{_esc(rotulo)} · {_esc(s)}: {_esc(_fmt(v, casas))} '
                f'{_esc(unidade)}</title>'
                f'<path d="{d}" fill="{_cor(series.index(s))}"/>'
                f'</g>')
            x += w
        partes.append(
            f'<text class="rotulo" x="{LABEL_WIDTH - 10}" '
            f'y="{y + BAR_HEIGHT * 0.72:.2f}" text-anchor="end">{_esc(rotulo)}</text>')
        partes.append(
            f'<text class="valor" x="{LABEL_WIDTH + escala(totais[i]) + 8:.2f}" '
            f'y="{y + BAR_HEIGHT * 0.72:.2f}">{_esc(_fmt(totais[i], casas))}</text>')
    partes.append(f'<line class="eixo" x1="{LABEL_WIDTH}" y1="{PAD_TOP}" '
                  f'x2="{LABEL_WIDTH}" y2="{PAD_TOP + altura_plot}"/>')

    y_leg = PAD_TOP + altura_plot + 22
    x_leg = float(LABEL_WIDTH)
    for k, s in enumerate(series):
        partes.append(f'<rect class="chave" x="{x_leg:.2f}" y="{y_leg - 8:.2f}" '
                      f'width="10" height="10" rx="2" fill="{_cor(k)}"/>')
        partes.append(f'<text class="legenda" x="{x_leg + 15:.2f}" y="{y_leg:.2f}">'
                      f'{_esc(s)}</text>')
        x_leg += 15 + 7.6 * len(s) + 18
        if x_leg > WIDTH - 90:
            x_leg = float(LABEL_WIDTH)
            y_leg += 18
            altura += 18
    partes.append(f'<text class="unidade" x="{LABEL_WIDTH}" y="{altura - 8}">'
                  f'{_esc(unidade)}</text>')
    return _svg(partes, altura, titulo)


def _cor(indice: int) -> str:
    if indice >= SERIES_SLOTS:
        return OTHER_ROLE
    return f"var(--serie-{indice + 1})"


def _svg(partes: list[str], altura: float, titulo: str) -> str:
    rotulo = f'<title>{_esc(titulo)}</title>' if titulo else ""
    return (f'<svg class="grafico" viewBox="0 0 {WIDTH} {altura:.0f}" '
            f'role="img" aria-label="{_esc(titulo)}" '
            f'preserveAspectRatio="xMidYMid meet">{rotulo}'
            + "".join(partes) + "</svg>")


def top_series(rows: list[tuple[str, dict]], *, limite: int = SERIES_SLOTS,
               rotulo_outros: str = "Outros") -> tuple[list[tuple[str, dict]], list[str]]:
    """Keep the `limite` largest categories and fold the rest into one.

    A ninth series never becomes a ninth hue. What it becomes is "Outros", in
    the chrome's muted ink, which is also the honest thing to draw: those
    categories are not individually readable at this size anyway.
    """
    total = {}
    for _, valores in rows:
        for k, v in valores.items():
            total[k] = total.get(k, 0.0) + float(v or 0.0)
    ordenadas = [k for k, _ in sorted(total.items(), key=lambda kv: -kv[1])]
    mantidas = ordenadas[:limite]
    if len(ordenadas) <= limite:
        return rows, mantidas
    novas = []
    for rotulo, valores in rows:
        v = {k: float(valores.get(k, 0.0)) for k in mantidas}
        v[rotulo_outros] = sum(float(val or 0.0) for k, val in valores.items()
                               if k not in mantidas)
        novas.append((rotulo, v))
    return novas, [*mantidas, rotulo_outros]
