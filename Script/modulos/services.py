from __future__ import annotations
import time
import pandas as pd
import numpy as np

from . import settings
from .naming import COLUMN_ORDER
from .metrics import metrics_from_prices, add_risk
from .datasources import fetch_prices, get_fundamentals, dy12m_yahoo, avg_volume_30d

def build_ranking(ativos: list[str]) -> pd.DataFrame:
    rows = []
    for a in ativos:
        prices = fetch_prices(a)
        m = metrics_from_prices(prices)
        f = get_fundamentals(a, use_js=False)

        last_price = float(prices.dropna().iloc[-1]) if not prices.dropna().empty else None
        dy_yf = dy12m_yahoo(a, last_price)
        liq_yf = avg_volume_30d(a)

        rows.append({
            "ativo": a,
            "segmento": f.segmento,
            "retorno_12m": m.retorno_12m,
            "vol_anual": m.vol_anual,
            "dd_max_2a": m.dd_max_2a,
            "preco_yf": last_price,
            "p_vp": f.p_vp,
            "dy12m_site": f.dy12m,
            "liq_diaria_site": f.liq_diaria,
            "dy12m_yf": dy_yf,
            "liq_media_30d": liq_yf,
        })
        time.sleep(0.2)  # rate-limit leve

    df = pd.DataFrame(rows)

    # tipagem/numérico
    numeric = ["retorno_12m","vol_anual","dd_max_2a","preco_yf","p_vp","dy12m_site","liq_diaria_site","dy12m_yf","liq_media_30d"]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ativo"] = df["ativo"].astype("string")
    df["segmento"] = df["segmento"].astype("string")

    df = add_risk(df)
    # ordem padrão de colunas
    return df[[c for c in COLUMN_ORDER if c in df.columns]]
