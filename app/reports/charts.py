"""
app/reports/charts.py
──────────────────────
Generazione grafici Plotly (Python) → PNG bytes per il report PDF.
Tema dark identico alla piattaforma web.

Funzioni esportate:
  chart_barre_kpi()     → barre orizzontali per penetrazione/ricordo/ingaggio
  chart_scatter_mappa() → scatter mappa canali (Pen vs Utilità, size=Ingaggio)
  chart_ocv_mix()       → barre orizzontali top mix per OCV%
"""

from __future__ import annotations

import io
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# ── Palette colori dark theme ────────────────────────────────────────────────
BG_PAPER  = "#161B27"   # surface_800
BG_PLOT   = "#1C2333"   # surface_700
FONT_CLR  = "#FFFFFF"
MUTED_CLR = "#6B6B6B"   # white_40
TEAL      = "#00A896"
TEAL_MID  = "#028090"
NAVY      = "#1E2761"
GREEN_OK  = "#02C39A"
RED_KO    = "#E53E3E"
ORANGE    = "#F77F00"

FONT_FAMILY = "Arial, Helvetica, sans-serif"

# ── Layout base dark ──────────────────────────────────────────────────────────

def _dark_layout(title: str = "", width: int = 700, height: int = 220,
                 margin: dict | None = None) -> dict:
    if margin is None:
        margin = dict(l=8, r=90, t=30, b=8)
    return dict(
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(color=FONT_CLR, family=FONT_FAMILY, size=10),
        title=dict(
            text=title,
            font=dict(color=TEAL, size=12, family=FONT_FAMILY),
            x=0, xanchor="left",
            pad=dict(l=8),
        ),
        width=width,
        height=height,
        margin=margin,
    )


def _to_png(fig: go.Figure) -> bytes:
    """Converte una figure Plotly in PNG bytes via kaleido."""
    return pio.to_image(fig, format="png", scale=2)


# ── Chart 1: Barre orizzontali KPI ───────────────────────────────────────────

def chart_barre_kpi(
    df: pd.DataFrame,
    col_canale: str,
    col_valore: str,
    colore: str = TEAL,
    titolo: str = "",
    top_n: int = 10,
    unit: str = "%",
) -> bytes:
    """
    Grafico a barre orizzontali per un KPI (penetrazione, ricordo, ingaggio).
    Top_n canali, ordinati decrescenti (il più alto appare in cima).

    Args:
        df:         DataFrame con colonne col_canale e col_valore
        col_canale: nome colonna canale (es. "Canale")
        col_valore: nome colonna valore (es. "Penetrazione (%)")
        colore:     hex colore barre
        titolo:     titolo grafico
        top_n:      numero massimo canali
        unit:       unità di misura per le etichette
    """
    df = df.dropna(subset=[col_canale, col_valore]).copy()
    df = df.nlargest(top_n, col_valore).sort_values(col_valore, ascending=True)

    vals  = df[col_valore].round(1).tolist()
    names = df[col_canale].tolist()
    texts = [f"{v}{unit}" for v in vals]

    # Colore barre con alpha per varietà visiva
    bar_colors = [colore] * len(vals)

    fig = go.Figure(go.Bar(
        x=vals,
        y=names,
        orientation="h",
        marker=dict(
            color=bar_colors,
            line=dict(color=BG_PLOT, width=0.5),
        ),
        text=texts,
        textposition="outside",
        textfont=dict(color=FONT_CLR, size=9),
        hovertemplate="%{y}: %{x:.1f}" + unit + "<extra></extra>",
    ))

    layout = _dark_layout(titolo, width=700, height=max(150, 22 * len(names) + 40))
    layout["xaxis"] = dict(
        showgrid=True,
        gridcolor=BG_PAPER,
        gridwidth=0.5,
        color=MUTED_CLR,
        zeroline=False,
        range=[0, max(vals) * 1.25 if vals else 100],
    )
    layout["yaxis"] = dict(
        color=FONT_CLR,
        tickfont=dict(size=9.5),
    )
    layout["margin"] = dict(l=8, r=80, t=35, b=8)
    fig.update_layout(**layout)

    return _to_png(fig)


# ── Chart 2: Scatter mappa canali ────────────────────────────────────────────

def chart_scatter_mappa(df_mappa: pd.DataFrame) -> bytes:
    """
    Scatter plot: asse X = Penetrazione (%), asse Y = Utilità media (1-7),
    dimensione bolla proporzionale a Ingaggio totale (%).
    4 quadranti calcolati sulla mediana di X e Y.
    """
    df = df_mappa.dropna(subset=["Penetrazione (%)", "Utilità media (1-7)"]).copy()
    if df.empty:
        # fallback: empty chart
        fig = go.Figure()
        fig.update_layout(**_dark_layout("Mappa Canali", width=700, height=320))
        return _to_png(fig)

    x_vals = df["Penetrazione (%)"].round(1)
    y_vals = df["Utilità media (1-7)"].round(2)
    ing    = df.get("Ingaggio totale (%)", pd.Series([10] * len(df)))

    # Normalizza size bolle (min 12, max 40)
    ing_clean = ing.fillna(ing.mean())
    if ing_clean.max() > ing_clean.min():
        size = 12 + 28 * (ing_clean - ing_clean.min()) / (ing_clean.max() - ing_clean.min())
    else:
        size = [20] * len(df)

    x_med = x_vals.median()
    y_med = y_vals.median()

    # Colori per quadrante
    colors = []
    for x, y in zip(x_vals, y_vals):
        if x >= x_med and y >= y_med:
            colors.append(TEAL)       # Alto Valore
        elif x < x_med and y >= y_med:
            colors.append(ORANGE)     # Da Sviluppare
        elif x >= x_med and y < y_med:
            colors.append(GREEN_OK)   # Quick Win
        else:
            colors.append(MUTED_CLR)  # Secondari

    fig = go.Figure()

    # Linee mediana (quadranti)
    fig.add_vline(x=float(x_med), line=dict(color=MUTED_CLR, dash="dash", width=0.8))
    fig.add_hline(y=float(y_med), line=dict(color=MUTED_CLR, dash="dash", width=0.8))

    # Annotazioni quadranti
    x_max = float(x_vals.max())
    y_max = float(y_vals.max())
    x_min = float(x_vals.min())
    y_min = float(y_vals.min())

    for (qx, qy, label) in [
        (x_max * 0.95, y_max * 0.97, "Alto Valore"),
        (x_min * 1.1,  y_max * 0.97, "Da Sviluppare"),
        (x_max * 0.95, y_min * 1.05, "Quick Win"),
        (x_min * 1.1,  y_min * 1.05, "Secondari"),
    ]:
        fig.add_annotation(
            x=qx, y=qy, text=label,
            showarrow=False,
            font=dict(size=8, color=MUTED_CLR),
            xanchor="right" if qx > float(x_med) else "left",
        )

    # Scatter bubbles
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="markers+text",
        marker=dict(
            size=size,
            color=colors,
            opacity=0.85,
            line=dict(color=BG_PAPER, width=1),
        ),
        text=df["Canale"].tolist(),
        textposition="top center",
        textfont=dict(size=8, color=FONT_CLR),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Penetrazione: %{x:.1f}%<br>"
            "Utilità: %{y:.2f}/7<extra></extra>"
        ),
    ))

    layout = _dark_layout("Mappa Canali — Penetrazione vs Utilità", width=700, height=280,
                          margin=dict(l=8, r=20, t=40, b=30))
    layout["xaxis"] = dict(
        title=dict(text="Penetrazione (%)", font=dict(size=9, color=MUTED_CLR)),
        color=MUTED_CLR, gridcolor=BG_PAPER, zeroline=False,
    )
    layout["yaxis"] = dict(
        title=dict(text="Utilità media (1-7)", font=dict(size=9, color=MUTED_CLR)),
        color=MUTED_CLR, gridcolor=BG_PAPER, zeroline=False,
    )
    fig.update_layout(**layout)
    return _to_png(fig)


# ── Chart 3: OCV Mix ─────────────────────────────────────────────────────────

def chart_ocv_mix(df_mix: pd.DataFrame, top_n: int = 10) -> bytes:
    """
    Barre orizzontali: top mix canali per OCV%.
    Colore verde se OCV>0 (sinergia), rosso se OCV<0 (saturazione).
    """
    df = df_mix.dropna(subset=["OCV (%)"]).copy()
    df = df.head(top_n).sort_values("OCV (%)", ascending=True)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(**_dark_layout("OCV Mix", width=700, height=220))
        return _to_png(fig)

    vals   = df["OCV (%)"].round(1).tolist()
    names  = df["Channel Mix"].tolist()
    colors = [GREEN_OK if v >= 0 else RED_KO for v in vals]
    texts  = [f"{v:+.1f}%" for v in vals]

    fig = go.Figure(go.Bar(
        x=vals,
        y=names,
        orientation="h",
        marker=dict(color=colors, line=dict(color=BG_PLOT, width=0.5)),
        text=texts,
        textposition="outside",
        textfont=dict(color=FONT_CLR, size=8.5),
        hovertemplate="%{y}<br>OCV: %{x:.1f}%<extra></extra>",
    ))

    x_abs_max = max(abs(min(vals, default=0)), abs(max(vals, default=0)))
    layout = _dark_layout("Top Mix Canali per OCV (%)", width=700,
                           height=max(180, 26 * len(names) + 60),
                           margin=dict(l=8, r=90, t=40, b=8))
    layout["xaxis"] = dict(
        showgrid=True,
        gridcolor=BG_PAPER,
        color=MUTED_CLR,
        zeroline=True,
        zerolinecolor=TEAL,
        zerolinewidth=1,
        range=[-(x_abs_max * 1.3), x_abs_max * 1.3],
    )
    layout["yaxis"] = dict(color=FONT_CLR, tickfont=dict(size=8.5))
    fig.update_layout(**layout)
    return _to_png(fig)
