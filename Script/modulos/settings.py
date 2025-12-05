# modulos/settings.py
from __future__ import annotations

BASE_URL = "https://investidor10.com.br/fiis"

# Fallback caso o Mongo falhe / não esteja configurado
_FALLBACK_ATIVOS = [
    "KNCR11","KNIP11","XPML11","HGLG11","MXRF11","VISC11","XPLG11","KNRI11",
    "BTLG11","HGBS11","BRCO11","BCIA11","RECT11","GGRC11",
    "VILG11","PATC11","HSML11",
]

try:
    from .mongo_fiis import get_all_fii_codes
    DEFAULT_ATIVOS = get_all_fii_codes()
    # se por algum motivo voltar lista vazia, usa o fallback
    if not DEFAULT_ATIVOS:
        DEFAULT_ATIVOS = _FALLBACK_ATIVOS
except Exception:
    DEFAULT_ATIVOS = _FALLBACK_ATIVOS


# requests / scraping
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124 Safari/537.36"
    )
}
HTTP_TIMEOUT = 20

# yfinance
YF_PRICE_PERIOD = "2y"      # preços
YF_VOL_PERIOD   = "3mo"     # p/ volume 30d

# cache HTTP (requests-cache)
CACHE_NAME   = "i10_cache"
CACHE_EXPIRE = 24 * 3600    # 24h
