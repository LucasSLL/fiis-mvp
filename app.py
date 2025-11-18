# app.py
# ---------------------------------------------------------
# FIIs – MVP (Investidor10 + yfinance)
# Projeto educacional. Não é recomendação de investimento.
# ---------------------------------------------------------

import re
import time
import math
import platform
import asyncio
import requests
import requests_cache
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
from bs4 import BeautifulSoup
from requests_html import HTMLSession

# --- (Windows) correção do event loop p/ requests_html/pyppeteer ---
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# ============= CONFIG =============
BASE_URL = "https://investidor10.com.br/fiis"
DEFAULT_TICKERS = [
    "KNCR11","KNIP11","XPML11","HGLG11","MXRF11","VISC11","XPLG11","KNRI11",
    "BTLG11","BCFF11","HGBS11","BRCO11","BCIA11","RECT11","GGRC11",
    "VILG11","PATC11","BTCR11","HSML11"
]

# cache leve (evita bater no site de novo por 24h)
requests_cache.install_cache("i10_cache", expire_after=24*3600)

st.set_page_config(page_title="FIIs MVP – Ranking & Busca", layout="wide")
st.title("FIIs – MVP (Investidor10 + yfinance)")
st.caption("Projeto educacional. Não é recomendação de investimento.")

# ============= PREÇOS & MÉTRICAS =============
def yahoo_symbol(ticker: str) -> str:
    t = ticker.upper().strip()
    return t if t.endswith(".SA") else f"{t}.SA"

def fetch_prices(ticker: str, period="2y") -> pd.Series:
    t = yahoo_symbol(ticker)
    df = yf.download(t, period=period, auto_adjust=True, progress=False)
    if df.empty:
        return pd.Series(dtype=float, name=ticker)

    if "Close" in df.columns:
        s = df["Close"].copy()
    elif "Adj Close" in df.columns:
        s = df["Adj Close"].copy()
    else:
        return pd.Series(dtype=float, name=ticker)

    s.name = ticker
    return s

def max_drawdown(series: pd.Series) -> float:
    if series.dropna().empty:
        return np.nan
    roll_max = series.cummax()
    dd = series / roll_max - 1
    return float(dd.min())

def metrics_from_prices(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return {"ret_12m": np.nan, "vol_252d": np.nan, "maxdd_2y": np.nan}

    rets = s.pct_change().dropna()
    w = rets.tail(252)
    ret_12m = (1 + w).prod() - 1 if not w.empty else np.nan
    vol_252d = (w.std() * np.sqrt(252)) if len(w) > 1 else np.nan
    maxdd_2y = max_drawdown(s.tail(504))
    return {"ret_12m": float(ret_12m), "vol_252d": float(vol_252d), "maxdd_2y": float(maxdd_2y)}

def dy12m_yahoo(ticker: str, last_price: float | None = None) -> float:
    """DY 12m via Yahoo: soma dividendos 12m / último preço * 100."""
    try:
        t = yahoo_symbol(ticker)
        tk = yf.Ticker(t)

        # 1) tenta .dividends
        div = tk.dividends

        # 2) fallback: .actions['Dividends']
        if (div is None) or div.empty:
            acts = tk.actions
            if isinstance(acts, pd.DataFrame) and "Dividends" in acts:
                div = acts["Dividends"]

        # 3) fallback: history(period="1y", actions=True)
        if (div is None) or div.empty:
            hist = tk.history(period="1y", actions=True)
            if isinstance(hist, pd.DataFrame) and "Dividends" in hist:
                div = hist["Dividends"]

        if (div is None) or div.empty:
            return np.nan

        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.DateOffset(months=12)
        idx = div.index.tz_localize(None) if getattr(div.index, "tz", None) else div.index
        div = div[idx >= cutoff]
        div = div[div > 0]
        if div.empty:
            return np.nan

        if last_price is None:
            px = fetch_prices(ticker).dropna()
            if px.empty:
                return np.nan
            last_price = float(px.iloc[-1])

        return float(div.sum() / last_price * 100.0)
    except Exception:
        return np.nan

def avg_volume_30d(ticker: str) -> float:
    """Média do volume diário (30 pregões) via Yahoo."""
    try:
        t = yahoo_symbol(ticker)
        df = yf.download(t, period="3mo", auto_adjust=False, progress=False)
        if df.empty or "Volume" not in df.columns:
            return np.nan
        return float(df["Volume"].tail(30).mean())
    except Exception:
        return np.nan

# ============= INVESTIDOR10 (FUNDAMENTAIS) =============
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}

def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

def _num_pt(s: str) -> float:
    if s is None:
        return np.nan
    s = s.strip()
    s = re.sub(r"[^\d,.\-BkMk ]", "", s)  # remove símbolos
    mult = 1.0
    if " B" in s:
        mult, s = 1_000_000_000.0, s.replace(" B", "")
    if " M" in s:
        mult, s = 1_000_000.0, s.replace(" M", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s) * mult
    except Exception:
        return np.nan

def fetch_fii_page_static(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

def fetch_fii_page_js(url: str) -> BeautifulSoup | None:
    """Renderiza JS com requests_html + pyppeteer (mais lento)."""
    try:
        s = HTMLSession()
        r = s.get(url)
        r.html.render(timeout=30, sleep=1)  # primeira vez pode baixar Chromium
        return BeautifulSoup(r.html.html, "html.parser")
    except Exception:
        return None

def parse_fundamentals(soup: BeautifulSoup) -> dict:
    def neighbors_text(el, hops=6):
        seen = 0
        node = el.parent if hasattr(el, "parent") else el
        while node and seen < hops:
            sib = node.next_sibling
            while sib is not None:
                if getattr(sib, "name", None) not in ("script", "style"):
                    txt = _text(sib)
                    if txt:
                        yield txt
                sib = getattr(sib, "next_sibling", None)
            node = getattr(node, "parent", None)
            seen += 1

    def find_num_by_label(rx):
        lab = soup.find(string=re.compile(rx, re.I))
        if not lab:
            lab = soup.find(lambda tag: tag.name in ["th","span","p","td","div"] and re.search(rx, _text(tag), re.I))
        if not lab:
            return None
        for txt in neighbors_text(lab):
            if re.search(r"\d", txt):
                return txt
        return None

    def find_text_by_label(rx):
        lab = soup.find(string=re.compile(rx, re.I))
        if not lab:
            lab = soup.find(lambda tag: tag.name in ["th","span","p","td","div"] and re.search(rx, _text(tag), re.I))
        if not lab:
            return None
        for txt in neighbors_text(lab):
            if len(txt) < 80 and not txt.strip().startswith("{") and not re.search(r"^\s*[\d.,%MBk]+\s*$", txt):
                return txt
        return None

    if soup is None:
        return {"nome": None, "segmento": None, "pl": None, "pvp": None, "dy12m": None, "liq_diaria": None}

    nome = _text(soup.select_one("h1, .title, .asset-name"))
    seg  = find_text_by_label(r"Segmento|Tipo de Fundo|Tipo|Setor")
    pl   = _num_pt(find_num_by_label(r"Patrim[oô]nio\s+L[ií]quido|Patrim[oô]nio"))
    pvp  = _num_pt(find_num_by_label(r"P\/?VP|Pre[cç]o\/?Valor\s+Patrimonial"))
    dy   = _num_pt(find_num_by_label(r"Dividend\s?Yield|DY"))
    liq  = _num_pt(find_num_by_label(r"L[ií]quidez\s+Di[áa]ria|Liquidez"))

    return {
        "nome": (nome or None),
        "segmento": (seg or None),
        "pl": (float(pl) if pl==pl else None),
        "pvp": (float(pvp) if pvp==pvp else None),
        "dy12m": (float(dy) if dy==dy else None),
        "liq_diaria": (float(liq) if liq==liq else None),
    }

@st.cache_data(ttl=24*3600)
def get_fundamentals(ticker: str, use_js: bool = False) -> dict:
    """Scrape do Investidor10. Rápido (estático) por padrão; com JS como fallback."""
    url = f"{BASE_URL}/{ticker.lower()}/"
    soup = fetch_fii_page_static(url)
    if use_js and soup is None:
        soup = fetch_fii_page_js(url)
    return parse_fundamentals(soup)

# ============= RANKING (seed) =============
def build_ranking(tickers: list[str]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        prices = fetch_prices(t)
        m = metrics_from_prices(prices)
        f = get_fundamentals(t, use_js=False)  # rápido para a lista

        last_price = float(prices.dropna().iloc[-1]) if not prices.dropna().empty else None
        dy_yf = dy12m_yahoo(t, last_price)
        liq_yf = avg_volume_30d(t)

        rows.append({
            "ticker": t,
            "segmento": f.get("segmento") or None,
            "ret_12m": m.get("ret_12m"),
            "vol_252d": m.get("vol_252d"),
            "maxdd_2y": m.get("maxdd_2y"),
            "p_vp_site": f.get("pvp"),
            "dy12m_site_pct": f.get("dy12m"),
            "liq_diaria_site": f.get("liq_diaria"),
            "dy12m_yf_pct": dy_yf,
            "liq_media_30d": liq_yf,
        })
        time.sleep(0.2)  # rate limit leve

    df = pd.DataFrame(rows)

    # força numérico
    for c in ["ret_12m","vol_252d","maxdd_2y","p_vp_site","dy12m_site_pct","liq_diaria_site","dy12m_yf_pct","liq_media_30d"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ticker"] = df["ticker"].astype("string")
    df["segmento"] = df["segmento"].astype("string")

    # score 0–100 por percentis (vol mais baixa e DD menos profundo → menor score)
    vol_pct = df["vol_252d"].rank(pct=True, na_option="keep")
    dd_pct  = df["maxdd_2y"].abs().rank(pct=True, na_option="keep")
    df["risk_score"] = (0.6*vol_pct + 0.4*dd_pct) * 100
    df["risk_label"] = pd.cut(df["risk_score"], bins=[-1,35,65,101], labels=["Baixo","Médio","Alto"])

    return df

with st.spinner("Carregando ranking inicial..."):
    ranking = build_ranking(DEFAULT_TICKERS)

# ===== UI: RANKING =====
st.subheader("Ranking (seed de FIIs)")
order_col = st.selectbox(
    "Ordenar por",
    ["risk_score","ret_12m","vol_252d","maxdd_2y",
     "p_vp_site","dy12m_site_pct","liq_diaria_site",
     "dy12m_yf_pct","liq_media_30d"],
    index=0
)
ascending = order_col in ["p_vp_site","maxdd_2y"]  # p/VP menor “melhor”; drawdown mais negativo ordenar crescente
view = ranking.sort_values(order_col, ascending=ascending)[
    ["ticker","segmento","risk_label","risk_score",
     "ret_12m","vol_252d","maxdd_2y",
     "p_vp_site","dy12m_site_pct","liq_diaria_site",
     "dy12m_yf_pct","liq_media_30d"]
]
st.dataframe(
    view.style.format({
        "risk_score":"{:.1f}",
        "ret_12m":"{:.1%}",
        "vol_252d":"{:.1%}",
        "maxdd_2y":"{:.1%}",
        "p_vp_site":"{:.2f}",
        "dy12m_site_pct":"{:.2f}%",
        "liq_diaria_site":"{:,.0f}",
        "dy12m_yf_pct":"{:.2f}%",
        "liq_media_30d":"{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ===== UI: BUSCA POR TICKER =====
st.subheader("Pesquisar FII")
col_a, col_b = st.columns([3,1])
with col_a:
    query = st.text_input("Digite o ticker (ex.: KNCR11, MXRF11, VISC11)...", value="KNCR11").upper().strip()
with col_b:
    run = st.button("Analisar")

if run and query:
    series = fetch_prices(query)
    m = metrics_from_prices(series)

    last_price = float(series.dropna().iloc[-1]) if not series.dropna().empty else None
    dy_yf = dy12m_yahoo(query, last_price)
    liq_yf = avg_volume_30d(query)

    # fundamentos – com JS ativado para pegar campos que só aparecem após renderização
    f = get_fundamentals(query, use_js=True)

    # percentil do ticker dentro do ranking atual
    base_vol = pd.to_numeric(ranking["vol_252d"], errors="coerce")
    base_dd  = pd.to_numeric(ranking["maxdd_2y"].abs(), errors="coerce")
    vol_pct_q = pd.concat([base_vol, pd.Series([m["vol_252d"]], dtype=float)]).rank(pct=True).iloc[-1] if pd.notna(m["vol_252d"]) else np.nan
    dd_pct_q  = pd.concat([base_dd,  pd.Series([abs(m["maxdd_2y"])], dtype=float)]).rank(pct=True).iloc[-1] if pd.notna(m["maxdd_2y"]) else np.nan
    score_q = (0.6*np.nan_to_num(vol_pct_q) + 0.4*np.nan_to_num(dd_pct_q)) * 100

    st.markdown(f"### {query} — {(_text(f.get('nome')) or '').strip()}")
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Score (risco)", "N/D" if np.isnan(score_q) else f"{score_q:.1f}")
    k2.metric("Ret 12m", f"{(m['ret_12m'] or 0)*100:.2f}%")
    k3.metric("Vol 252d", f"{(m['vol_252d'] or 0)*100:.2f}%")
    k4.metric("Máx DD (2a)", f"{(m['maxdd_2y'] or 0)*100:.2f}%")
    pvp_val = f.get("pvp", np.nan)
    k5.metric("P/VP (site)", f"{pvp_val:.2f}" if not math.isnan(pvp_val) else "N/D")

    kk1,kk2,kk3 = st.columns(3)
    kk1.metric("Dividend Yield 12m (Yahoo)", f"{dy_yf:.2f}%" if not math.isnan(dy_yf) else "N/D")
    kk2.metric("Liq. diária média 30d (Yahoo)", f"{liq_yf:,.0f}" if not math.isnan(liq_yf) else "N/D")
    kk3.metric("Segmento (site)", f.get("segmento") or "N/D")

    st.markdown("**Preço (normalizado) – últimos 24 meses**")
    if series.dropna().empty:
        st.info("Sem dados de preço no Yahoo para este ticker.")
    else:
        last = series.tail(504)
        st.line_chart((last/last.dropna().iloc[0]).rename("Preço normalizado"))
        dd = last/last.cummax() - 1
        st.line_chart(dd.rename("Drawdown"))

    st.caption("Fontes: Investidor10 (fundamentais) • Yahoo Finance (preços/dividendos/volume).")
