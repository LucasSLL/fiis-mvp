# modulos/layout.py
from __future__ import annotations
import streamlit as st


def apply_global_style():
    """CSS e ajustes visuais globais."""
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #f5f5f7;
            }

            h1 {
                font-weight: 700;
            }

            .stTextInput > div > div > input {
                border-radius: 999px;
            }

            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 100%;
            }

            /* Tabs da direita – estilo pill */
            div[data-baseweb="tab-list"] {
                gap: 0.75rem;
            }

            button[data-baseweb="tab"] {
                border-radius: 999px;
                padding: 0.3rem 0.9rem;
                font-weight: 500;
                font-size: 0.9rem;
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                background-color: #f97316;   /* laranja suave */
                color: white;
            }

            /* Linha embaixo das abas (highlight) */
            .stTabs [data-baseweb="tab-highlight"] {
                background-color: transparent !important;
                height: 0 !important;
                border-radius: 0 !important;
            }

            /* Metrics como cartão */
            div[data-testid="stMetric"] {
                background-color: #ffffff;
                padding: 0.75rem 1rem;
                border-radius: 0.75rem;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
                text-align: center;
            }
            div[data-testid="stMetric"] label {
                font-size: 0.8rem;
                color: #6b7280;
            }
            div[data-testid="stMetricValue"] {
                font-size: 1.3rem;
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_header():
    """Cabeçalho padrão da página."""
    st.title("FIIs – Ranking & Busca")
    st.caption("Projeto educacional. Não é recomendação de investimento.")


def render_footer():
    """Rodapé padrão com fontes/observações."""
    st.caption(
        "Fontes: Investidor10 (fundamentais, DY 12m do site) • "
        "Yahoo Finance (preços/dividendos/volume).\n"
        "Obs.: o Retorno 12m usa preços ajustados do Yahoo (inclui efeito dos dividendos) "
        "e pode diferir dos números exibidos nos próprios sites."
    )


def render_price_charts(last, serie_norm, dd, dividends_monthly, mode="tabs"):
    """Bloco com todos os gráficos do ativo selecionado."""

    if mode == "stack":
        # --- Preço em R$ ---
        st.markdown("**Preço (R$) – últimos 24 meses**")
        df_preco = last.to_frame()
        df_preco.columns = ["Preço (R$)"]
        st.line_chart(df_preco)

        # --- Preço normalizado ---
        st.markdown("**Preço normalizado – últimos 24 meses**")
        st.line_chart(serie_norm.to_frame())

        # --- Drawdown ---
        st.markdown("**Drawdown (queda em relação à máxima) – últimos 24 meses**")
        st.line_chart(dd.to_frame())

        # --- Dividendos ---
        if not dividends_monthly.empty:
            st.markdown("**Dividendos pagos (Yahoo) – últimos 24 meses**")
            st.bar_chart(dividends_monthly)
        else:
            st.info("Sem dividendos registrados no período.")
        return  # sai da função aqui

    # ====== MODO “TABS” (compacto) ======
    tab_preco, tab_norm, tab_dd, tab_divs = st.tabs(
        ["Preço", "Preço normalizado", "Drawdown", "Dividendos"]
    )

    with tab_preco:
        st.markdown("**Preço (R$) – últimos 24 meses**")
        df_preco = last.to_frame()
        df_preco.columns = ["Preço (R$)"]
        st.line_chart(df_preco)

    with tab_norm:
        st.markdown("**Preço normalizado – últimos 24 meses**")
        st.line_chart(serie_norm.to_frame())

    with tab_dd:
        st.markdown("**Drawdown (queda em relação à máxima) – últimos 24 meses**")
        st.line_chart(dd.to_frame())

    with tab_divs:
        if dividends_monthly.empty:
            st.info("Sem dividendos registrados no período.")
        else:
            st.markdown("**Dividendos pagos (Yahoo) – últimos 24 meses**")
            st.bar_chart(dividends_monthly)

