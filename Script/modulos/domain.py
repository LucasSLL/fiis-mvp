from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Metrics:
    retorno_12m: Optional[float]
    vol_anual:   Optional[float]
    dd_max_2a:   Optional[float]

@dataclass
class Fundamentals:
    nome:        Optional[str]
    segmento:    Optional[str]
    p_vp:        Optional[float]
    dy12m:       Optional[float]
    liq_diaria:  Optional[float]

@dataclass
class AtivoFII:
    ativo:        str
    metrics:      Metrics
    fundamentals: Fundamentals
    dy12m_yf:     Optional[float]
    liq30d:       Optional[float]
