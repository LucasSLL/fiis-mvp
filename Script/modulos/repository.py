from __future__ import annotations
from pathlib import Path
import pandas as pd
import requests_cache
from . import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def init_http_cache():
    requests_cache.install_cache(settings.CACHE_NAME, expire_after=settings.CACHE_EXPIRE)

def save_df(df: pd.DataFrame, name: str):
    p = DATA_DIR / f"{name}.parquet"
    df.to_parquet(p, index=False)

def load_df(name: str) -> pd.DataFrame | None:
    p = DATA_DIR / f"{name}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return None
