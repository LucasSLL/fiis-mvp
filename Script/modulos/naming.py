# nomes canônicos do DataFrame + rótulos para UI + formatação

COLUMN_ORDER = [
    "ativo","segmento","class_risco","indice_risco",
    "retorno_12m","vol_anual","dd_max_2a",
    "preco_yf","p_vp","dy12m_site","liq_diaria_site",
    "dy12m_yf","liq_media_30d",
]

DISPLAY = {
    "ativo":            "Ativo",
    "segmento":         "Segmento",
    "class_risco":      "Risco",
    "indice_risco":     "Índice de Risco (0–100)",
    "retorno_12m":      "Retorno 12m (preço+dividendos, Yahoo)",
    "vol_anual":        "Volatilidade (anual)",
    "dd_max_2a":        "Drawdown Máx. (2a)",
    "preco_yf":         "Cotação (Yahoo)",
    "p_vp":             "P/VP",
    "dy12m_site":       "DY 12m (Site)",
    "liq_diaria_site":  "Liq. diária (Site)",
    "dy12m_yf":         "DY 12m (Yahoo)",
    "liq_media_30d":    "Liq. média (30d)",
}

FORMAT = {
    "indice_risco":     "{:.1f}",
    "retorno_12m":      "{:.1%}",
    "vol_anual":        "{:.1%}",
    "dd_max_2a":        "{:.1%}",
    "preco_yf":         "R$ {:,.2f}",
    "p_vp":             "{:.2f}",
    "dy12m_site":       "{:.2f}%",
    "dy12m_yf":         "{:.2f}%",
    "liq_diaria_site":  "{:,.0f}",
    "liq_media_30d":    "{:,.0f}",
}

DEFAULT_VIEW = [
    "ativo","segmento","class_risco","indice_risco",
    "retorno_12m","vol_anual","dd_max_2a","preco_yf","p_vp","dy12m_site","liq_media_30d"
]

ORDER_CHOICES = [
    "indice_risco","retorno_12m","vol_anual","dd_max_2a",
    "preco_yf","p_vp","dy12m_site","liq_diaria_site","dy12m_yf","liq_media_30d"
]
