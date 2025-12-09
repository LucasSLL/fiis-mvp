# app.py
import os
import sys
import math
import re
import streamlit as st
import pandas as pd

# deixa a pasta "Script" no sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modulos import settings
from modulos.repository import init_http_cache, save_df, load_df
from modulos.services import build_ranking
from modulos.naming import DISPLAY, FORMAT, DEFAULT_VIEW, ORDER_CHOICES
from modulos.datasources import fetch_prices, get_fundamentals, dy12m_yahoo, avg_volume_30d, dividends_history_yahoo
from modulos.metrics import metrics_from_prices
from modulos.layout import apply_global_style, render_header, render_price_charts, render_footer

# cache HTTP (requests-cache)
init_http_cache()

st.set_page_config(page_title="FIIs – Ranking & Busca", layout="wide")
apply_global_style()
render_header()

# guarda o último ticker analisado
if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = None

# --- Ranking inicial (com cache em disco opcional) ---
with st.spinner("Carregando ranking inicial..."):
    df_cached = load_df("ranking_seed")

    # se não tiver a coluna nova, força reconstrução
    if df_cached is not None and "preco_yf" in df_cached.columns:
        ranking = df_cached
    else:
        ranking = build_ranking(settings.DEFAULT_ATIVOS)
        save_df(ranking, "ranking_seed")

# lista de todos os tickers disponíveis no ranking
ALL_TICKERS = sorted(ranking["ativo"].str.upper().unique())

# ===== LAYOUT PRINCIPAL EM DUAS COLUNAS + ESPAÇO =====
col_left, col_right = st.columns([1.0, 1.1])  

# ---------- COLUNA ESQUERDA: RANKING ----------
with col_left:
    st.subheader("Ranking (seed de FIIs)")

    #label_to_canon = {DISPLAY[k]: k for k in DISPLAY}
    #order_col_label = st.selectbox(
    #    "Ordenar por",
    #    [DISPLAY[c] for c in ORDER_CHOICES],
    #    index=0,
    #)
    #order_col = label_to_canon[order_col_label]

    order_col = ORDER_CHOICES[0] 

    # P/VP menor “melhor”; DD mais negativo → crescente
    ascending = order_col in ["p_vp", "dd_max_2a"]

    view = ranking.sort_values(order_col, ascending=ascending)[DEFAULT_VIEW]
    view_display = view.rename(columns=DISPLAY)

    def color_value(val):
        if val == 'Alto':
            color = 'red'
        elif val == 'Baixo':
            color = 'green'
        elif val == 'Médio':
            color = 'yellow'
        else:
            color = 'white'
            
        return f'color: {color}'

    styled_df =  view_display.style.format(
                    {DISPLAY[k]: v for k, v in FORMAT.items() if k in view.columns}
                ).applymap(
                    color_value,
                    subset=['Risco']
                )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=1950,
    )

# ---------- COLUNA DIREITA: BUSCA + DETALHES ----------
with col_right:
    # UMA ÚNICA BARRA DE ABAS (com ícones)
    tab_fii, tab_carteira = st.tabs(["🔍 Análise do FII", "📊 Minha carteira"])

    # ===================== ABA 1: ANÁLISE DO FII =====================
    with tab_fii:
        st.subheader("Pesquisar FII")

        # ----- FORM DE BUSCA DENTRO DA ABA -----
        with st.form("busca_fii"):
            st.markdown("Digite o ativo (ex.: **KNCR11, MXRF11, VISC11**)...")

            col_a, col_b = st.columns([3, 1])
            with col_a:
                query = st.text_input(
                    label="",
                    placeholder="Ex.: MXRF11",
                    label_visibility="collapsed",
                    value=st.session_state.current_ticker or "",
                )
            with col_b:
                run = st.form_submit_button("Analisar", use_container_width=True)

        # Atualiza o ticker salvo se clicou em Analisar
        if run and query:
            ticker = query.strip().upper()
            if not re.fullmatch(r"[A-Z]{4}11", ticker):
                st.error("Você só pode inserir um código válido de um fundo imobiliário. Ex.: VGIR11")
            else:
                st.session_state.current_ticker = ticker

        ticker = st.session_state.current_ticker

        if not ticker:
            st.info("Digite um FII e clique em **Analisar** para ver os gráficos e métricas.")
        else:
            # --- Dados de preço / métricas / fundamentos ---
            series = fetch_prices(ticker)
            m = metrics_from_prices(series)

            last_price = float(series.dropna().iloc[-1]) if not series.dropna().empty else None
            dy_yf = dy12m_yahoo(ticker, last_price)
            liq_yf = avg_volume_30d(ticker)
            f = get_fundamentals(ticker, use_js=True)
            divs = dividends_history_yahoo(ticker, months=24)

            # --- Índice de risco ---
            smodulos_q = float("nan")
            linha_rank = ranking.loc[ranking["ativo"].str.upper() == ticker]

            if not linha_rank.empty and pd.notna(linha_rank["indice_risco"].iloc[0]):
                smodulos_q = float(linha_rank["indice_risco"].iloc[0])
            else:
                base_vol = pd.to_numeric(ranking["vol_anual"], errors="coerce")
                base_dd = pd.to_numeric(ranking["dd_max_2a"].abs(), errors="coerce")

                if pd.notna(m.vol_anual) and pd.notna(m.dd_max_2a):
                    vol_pct_q = pd.concat(
                        [base_vol, pd.Series([m.vol_anual], dtype=float)]
                    ).rank(pct=True).iloc[-1]

                    dd_pct_q = pd.concat(
                        [base_dd, pd.Series([abs(m.dd_max_2a)], dtype=float)]
                    ).rank(pct=True).iloc[-1]

                    smodulos_q = (0.6 * vol_pct_q + 0.4 * dd_pct_q) * 100

            # --- Cabeçalho e cards ---
            st.markdown(f"### {ticker}")

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Índice de Risco", "N/D" if pd.isna(smodulos_q) else f"{smodulos_q:.1f}")
            k2.metric("Retorno 12m (preço+dividendos, Yahoo)", f"{(m.retorno_12m or 0)*100:.2f}%")
            k3.metric("Vol. anual", f"{(m.vol_anual or 0)*100:.2f}%")
            k4.metric("Máx DD (2a)", f"{(m.dd_max_2a or 0)*100:.2f}%")
            k5.metric(
                "P/VP (site)",
                f"{f.p_vp:.2f}" if f.p_vp is not None and not math.isnan(f.p_vp) else "N/D",
            )

            kk1, kk2, kk3 = st.columns(3)
            kk1.metric("DY 12m (Yahoo)", f"{dy_yf:.2f}%" if dy_yf == dy_yf else "N/D")
            kk2.metric("Liq. média 30d (Yahoo)", f"{liq_yf:,.0f}" if liq_yf == liq_yf else "N/D")
            kk3.metric("Segmento (site)", f.segmento or "N/D")

            # --- Gráficos ---
            if series.dropna().empty:
                st.info("Sem dados de preço no Yahoo para este ativo.")
            else:
                last_prices = series.squeeze().tail(504)

                base = last_prices.dropna().iloc[0]
                serie_norm = last_prices / base
                serie_norm.name = "Preço normalizado"

                dd = last_prices / last_prices.cummax() - 1
                dd.name = "Drawdown"

                if divs.dropna().empty:
                    dividends_monthly = pd.Series(dtype="float64", name="Dividendos (R$)")
                else:
                    dividends_monthly = divs.resample("M").sum()
                    dividends_monthly.name = "Dividendos (R$)"

                view_mode = st.radio(
                    "Visualização dos gráficos",
                    ["Compacto (abas)", "Todos empilhados"],
                    horizontal=True,
                    key="view_mode",
                )

                mode_key = "tabs" if view_mode.startswith("Compacto") else "stack"
                render_price_charts(last_prices, serie_norm, dd, dividends_monthly, mode=mode_key)

    # ===================== ABA 2: MINHA CARTEIRA =====================
    with tab_carteira:
        st.subheader("Minha carteira")

        carteira = st.multiselect(
            "Selecione os FIIs que fazem parte da sua carteira:",
            options=ALL_TICKERS,
            default=[],
        )

        if carteira:
            df_carteira = ranking[ranking["ativo"].str.upper().isin(carteira)]

            c1, c2, c3 = st.columns(3)
            c1.metric("Qtd. de FIIs", len(df_carteira))

            if "indice_risco" in df_carteira.columns:
                risco_medio = df_carteira["indice_risco"].mean()
                c2.metric("Risco médio (0–100)", f"{risco_medio:.1f}")
            else:
                c2.metric("Risco médio (0–100)", "N/D")

            if "retorno_12m" in df_carteira.columns:
                ret_medio = df_carteira["retorno_12m"].mean() * 100
                c3.metric("Retorno médio 12m", f"{ret_medio:.2f}%")
            else:
                c3.metric("Retorno médio 12m", "N/D")

            st.dataframe(
                df_carteira[DEFAULT_VIEW].rename(columns=DISPLAY).style.format(
                    {DISPLAY[k]: v for k, v in FORMAT.items() if k in df_carteira.columns}
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Selecione alguns FIIs acima para ver o resumo da sua carteira.")

# ===== RODAPÉ (FULL WIDTH) =====
st.markdown("---")
render_footer()