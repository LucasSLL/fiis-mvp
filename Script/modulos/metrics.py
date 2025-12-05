from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .domain import Metrics

def max_drawdown(series: pd.Series) -> float:
    s = series.dropna()
    if s.empty:
        return float("nan")
    roll_max = s.cummax()
    dd = s / roll_max - 1
    return float(dd.min())

def metrics_from_prices(series: pd.Series) -> Metrics:
    """
    Calcula:
      - retorno_12m: retorno acumulado dos últimos ~252 pregões
      - vol_anual: volatilidade anualizada (252 pregões)
      - dd_max_2a: drawdown máximo em ~2 anos (504 pregões)
    Retorna None quando não há dados suficientes.
    """
    s = series.dropna()
    if s.empty:
        return Metrics(None, None, None)

    rets = s.pct_change().dropna()
    w = rets.tail(252)

    if w.empty:
        ret_12m_val = float("nan")
        vol_252d_val = float("nan")
    else:
        ret_12m_val = float((1 + w).prod() - 1)
        vol_252d_val = float(w.std() * math.sqrt(252)) if len(w) > 1 else float("nan")

    dd_2y_val = float(max_drawdown(s.tail(504)))

    def none_if_nan(x: float):
        return None if math.isnan(x) else x

    return Metrics(
        none_if_nan(ret_12m_val),
        none_if_nan(vol_252d_val),
        none_if_nan(dd_2y_val),
    )

def add_risk(df: pd.DataFrame) -> pd.DataFrame:
    # percentis: quanto maior vol/abs(DD), maior o score
    vol_pct = df["vol_anual"].rank(pct=True, na_option="keep")
    dd_pct = df["dd_max_2a"].abs().rank(pct=True, na_option="keep")

    df["indice_risco"] = (0.6 * vol_pct + 0.4 * dd_pct) * 100
    df["class_risco"] = pd.cut(
        df["indice_risco"],
        bins=[-1, 35, 65, 101],
        labels=["Baixo", "Médio", "Alto"],
    )
    return df
