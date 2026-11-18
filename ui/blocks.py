"""Blocos de HTML da camada visual, montados com Jinja2 (autoescape ligado)."""

from __future__ import annotations

import jinja2
import streamlit as st

from . import theme

_ENV = jinja2.Environment(autoescape=True)

_HERO = _ENV.from_string("""
<div class="i3-hero">
  <div>
    <small>{{ kicker }}</small>
    <h1>{{ title }}</h1>
    <p>{{ text }}</p>
    <div class="i3-types">
      {% for label, active in types -%}
      <span{% if active %} class="active"{% endif %}>{{ label }}</span>
      {%- endfor %}
    </div>
  </div>
  <img src="data:image/png;base64,{{ logo }}" alt="i3ET logo">
</div>
""")

_COLUMN_TITLE = _ENV.from_string('<div class="i3-col-title">{{ label }}</div>')


def hero(*, kicker: str, title: str, text: str, types: list[tuple[str, bool]]) -> None:
    st.markdown(_HERO.render(kicker=kicker, title=title, text=text, types=types,
                             logo=theme.asset_b64("i3et-logo.png")), unsafe_allow_html=True)


def column_title(label: str) -> None:
    st.markdown(_COLUMN_TITLE.render(label=label), unsafe_allow_html=True)
