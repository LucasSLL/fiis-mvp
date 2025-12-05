from __future__ import annotations
import re, math, platform, asyncio
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from bs4 import BeautifulSoup

from . import settings
from .domain import Fundamentals
from .metrics import metrics_from_prices

# suporte opcional a requests_html (JS render)
try:
    from requests_html import HTMLSession
except Exception:
    HTMLSession = None  # manter compatível sem esse pacote

# Windows: event loop para requests_html/pyppeteer
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

def yahoo_symbol(ativo: str) -> str:
    t = ativo.upper().strip()
    return t if t.endswith(".SA") else f"{t}.SA"

def fetch_prices(ativo: str, period: str = settings.YF_PRICE_PERIOD) -> pd.Series:
    t = yahoo_symbol(ativo)
    df = yf.download(t, period=period, auto_adjust=True, progress=False)
    if df.empty:
        return pd.Series(dtype=float, name=ativo)
    s = df["Close"] if "Close" in df.columns else df.get("Adj Close", pd.Series(dtype=float))
    s = s.copy()
    s.name = ativo
    return s

def dy12m_yahoo(ativo: str, last_price: float | None = None) -> float:
    try:
        tk = yf.Ticker(yahoo_symbol(ativo))
        div = tk.dividends

        if (div is None) or div.empty:
            acts = tk.actions
            if isinstance(acts, pd.DataFrame) and "Dividends" in acts:
                div = acts["Dividends"]
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
            px = fetch_prices(ativo).dropna()
            if px.empty:
                return np.nan
            last_price = float(px.iloc[-1])

        return float(div.sum() / last_price * 100.0)
    except Exception:
        return np.nan

def dividends_history_yahoo(ativo: str, months: int = 24) -> pd.Series:
    """
    Retorna a série de dividendos do Yahoo para os últimos `months` meses.
    Cada ponto é um pagamento de dividendo na data correspondente.
    """
    try:
        tk = yf.Ticker(yahoo_symbol(ativo))
        div = tk.dividends

        # fallbacks iguais aos do dy12m_yahoo
        if (div is None) or div.empty:
            acts = tk.actions
            if isinstance(acts, pd.DataFrame) and "Dividends" in acts:
                div = acts["Dividends"]
        if (div is None) or div.empty:
            hist = tk.history(period=f"{months}mo", actions=True)
            if isinstance(hist, pd.DataFrame) and "Dividends" in hist:
                div = hist["Dividends"]

        if (div is None) or div.empty:
            return pd.Series(dtype=float, name="Dividendos")

        # filtra por período e só valores > 0
        idx = div.index.tz_localize(None) if getattr(div.index, "tz", None) else div.index
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.DateOffset(months=months)
        div = div[(idx >= cutoff) & (div > 0)]
        div.name = "Dividendos"
        return div
    except Exception:
        return pd.Series(dtype=float, name="Dividendos")


def avg_volume_30d(ativo: str) -> float:
    try:
        t = yahoo_symbol(ativo)
        df = yf.download(t, period=settings.YF_VOL_PERIOD, auto_adjust=False, progress=False)
        if df.empty or "Volume" not in df.columns:
            return np.nan
        return float(df["Volume"].tail(30).mean())
    except Exception:
        return np.nan

# --------- scraping Investidor10 ----------
def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

def _num_pt(s: str) -> float:
    if s is None: return np.nan
    s = s.strip()
    s = re.sub(r"[^\d,.\-BkMk ]", "", s)
    mult = 1.0
    if " B" in s: mult, s = 1_000_000_000.0, s.replace(" B", "")
    if " M" in s: mult, s = 1_000_000.0, s.replace(" M", "")
    s = s.replace(".", "").replace(",", ".")
    try: return float(s) * mult
    except: return np.nan

def _fetch_fii_page_static(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=settings.HEADERS, timeout=settings.HTTP_TIMEOUT)
        if r.status_code != 200: return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

def _fetch_fii_page_js(url: str) -> BeautifulSoup | None:
    if HTMLSession is None:
        return None
    try:
        s = HTMLSession()
        r = s.get(url); r.html.render(timeout=30, sleep=1)
        return BeautifulSoup(r.html.html, "html.parser")
    except Exception:
        return None

def _parse_fundamentals(soup: BeautifulSoup) -> Fundamentals:
    # Se não conseguiu baixar a página, devolve tudo None
    if soup is None:
        return Fundamentals(None, None, None, None, None)

    # ---- Nome do fundo (título da página) ----
    nome = _text(soup.select_one("h1, .title, .asset-name")) or None

    # remove o sufixo "Minha Carteira" do título, se existir
    if nome:
        # remove " - Minha Carteira", " — Minha Carteira", etc.
        nome = re.sub(r"\s*[-–—]\s*Minha Carteira.*$", "", nome, flags=re.I).strip()


    # ------------------------------------------------------------------
    # 1) Tipo de fundo + Segmento em formato curto: "Papel / Híbrido",
    #    "Tijolo / Shoppings e Varejo", etc.
    # ------------------------------------------------------------------
    tipo_txt = None
    seg_txt = None

    # Texto da seção "Sobre a ..." (ex.: "é um fundo imobiliário do tipo Fundo de papel e do segmento Híbrido.")
    sobre = soup.find(string=re.compile(r"fundo imobili[aá]rio do tipo", re.I))
    if sobre:
        txt = _text(sobre.parent if hasattr(sobre, "parent") else sobre)
        m = re.search(r"tipo\s+(.+?)\s+e do segmento\s+(.+?)[\.,]", txt, re.I)
        if m:
            tipo_txt = m.group(1).strip()
            seg_txt = m.group(2).strip()

    # Fallback: tentar pegar diretamente rótulos "TIPO DE FUNDO" e "SEGMENTO"
    def _find_text_by_label(rx):
        lab = soup.find(string=re.compile(rx, re.I)) or \
              soup.find(
                  lambda tag: tag.name in ["th", "span", "p", "td", "div"]
                  and re.search(rx, _text(tag), re.I)
              )
        if not lab:
            return None
        # pega textos próximos (irmãos / pais)
        node = lab.parent if hasattr(lab, "parent") else lab
        hops = 0
        while node and hops < 4:
            sib = node.next_sibling
            while sib is not None:
                if getattr(sib, "name", None) not in ("script", "style"):
                    txt2 = _text(sib)
                    if txt2 and len(txt2) < 80 and not re.search(r"^\s*[\d.,%MBk]+\s*$", txt2):
                        return txt2.strip()
                sib = getattr(sib, "next_sibling", None)
            node = getattr(node, "parent", None)
            hops += 1
        return None

    if not tipo_txt:
        tipo_txt = _find_text_by_label(r"Tipo de Fundo")

    if not seg_txt:
        seg_txt = _find_text_by_label(r"\bSegmento\b")

    # Limpa tipo ("Fundo de papel" -> "Papel")
    def _short_tipo(t: str | None) -> str | None:
        if not t:
            return None
        t = re.sub(r"(?i)^fundo[s]?\s+de\s+", "", t).strip()
        return t or None

    tipo_clean = _short_tipo(tipo_txt)
    seg_clean = seg_txt.strip() if seg_txt else None

    if tipo_clean and seg_clean:
        segmento_final = f"{tipo_clean} / {seg_clean}"
    else:
        segmento_final = tipo_clean or seg_clean

    # ------------------------------------------------------------------
    # 2) P/VP – varremos o texto inteiro e procuramos "P/VP 0,39"
    # ------------------------------------------------------------------
    full_text = _text(soup)
    m_pvp = re.search(r"P\/?VP\s*[:\-]?\s*([\d.,]+)", full_text, re.I)
    pvp_val = _num_pt(m_pvp.group(1)) if m_pvp else float("nan")

    # ------------------------------------------------------------------
    # 3) DY 12m – usa padrão "DY (12M) 12,49%"
    # ------------------------------------------------------------------
    dy_val = float("nan")

    # tenta primeiro a forma "DY (12M) 12,49%"
    m_dy = re.search(r"DY\s*\(12M\)[^0-9\-]*([\d.,]+)", full_text, re.I)
    if m_dy:
        dy_val = _num_pt(m_dy.group(1))
    else:
        # fallback genérico, em cima dos rótulos
        def _find_num_by_label(rx):
            lab = soup.find(string=re.compile(rx, re.I)) or \
                  soup.find(
                      lambda tag: tag.name in ["th", "span", "p", "td", "div"]
                      and re.search(rx, _text(tag), re.I)
                  )
            if not lab:
                return None
            node = lab.parent if hasattr(lab, "parent") else lab
            hops = 0
            while node and hops < 4:
                sib = node.next_sibling
                while sib is not None:
                    if getattr(sib, "name", None) not in ("script", "style"):
                        txt2 = _text(sib)
                        if txt2 and re.search(r"\d", txt2):
                            return txt2
                    sib = getattr(sib, "next_sibling", None)
                node = getattr(node, "parent", None)
                hops += 1
            return None

        dy_str = _find_num_by_label(r"Dividend\s?Yield|Dividend\s?Yeld|DY")
        if dy_str is not None:
            dy_val = _num_pt(dy_str)

    # ------------------------------------------------------------------
    # 4) Liquidez Diária – padrão "Liquidez Diária  R$ 366,41 K"
    # ------------------------------------------------------------------
    liq_val = float("nan")

    # tenta direto no texto inteiro
    m_liq = re.search(
        r"Liquidez\s+Di[áa]ria[^0-9\-]*R?\$?\s*([\d.,]+\s*[KMBkmb]?)",
        full_text,
        re.I,
    )
    if m_liq:
        liq_val = _num_pt(m_liq.group(1))
    else:
        # fallback usando rótulos, se necessário
        def _find_num_by_label(rx):
            lab = soup.find(string=re.compile(rx, re.I)) or \
                  soup.find(
                      lambda tag: tag.name in ["th", "span", "p", "td", "div"]
                      and re.search(rx, _text(tag), re.I)
                  )
            if not lab:
                return None
            node = lab.parent if hasattr(lab, "parent") else lab
            hops = 0
            while node and hops < 4:
                sib = node.next_sibling
                while sib is not None:
                    if getattr(sib, "name", None) not in ("script", "style"):
                        txt2 = _text(sib)
                        if txt2 and re.search(r"\d", txt2):
                            return txt2
                    sib = getattr(sib, "next_sibling", None)
                node = getattr(node, "parent", None)
                hops += 1
            return None

        liq_str = _find_num_by_label(r"L[ií]quidez\s+Di[áa]ria|Liquidez")
        if liq_str is not None:
            liq_val = _num_pt(liq_str)

    # ------------------------------------------------------------------
    # 5) Monta o dataclass com os valores
    # ------------------------------------------------------------------
    return Fundamentals(
        nome,
        segmento_final,
        float(pvp_val) if pvp_val == pvp_val else None,
        float(dy_val) if dy_val == dy_val else None,
        float(liq_val) if liq_val == liq_val else None,
    )



def get_fundamentals(ativo: str, use_js: bool = False) -> Fundamentals:
    url = f"{settings.BASE_URL}/{ativo.lower()}/"
    soup = _fetch_fii_page_static(url)
    if use_js and soup is None:
        soup = _fetch_fii_page_js(url)
    return _parse_fundamentals(soup)
