# FIIs – MVP (Investidor10 + yfinance)

Projeto educacional que monta um **ranking de FIIs** e permite **pesquisar um ativo** para ver métricas de risco e desempenho.

> **Aviso**: não é recomendação de investimento.

## Funcionalidades
- Ranking com seed de FIIs (ordenável por `risk_score`, retorno, volatilidade, etc.)
- Busca por FII (ex.: KNCR11) com métricas individuais
- **Risco (0–100)**: combinação de volatilidade 252d e drawdown máximo em 2 anos
- Dados de **preço** e **dividendos** via Yahoo Finance (`yfinance`)
- (Quando disponível) *indicadores fundamentais* do site Investidor10

## Stack
- Python 3.11
- Streamlit, pandas, numpy, yfinance
- requests, requests-cache, beautifulsoup4

## Como rodar localmente
```bash
# Recomendado: criar ambiente
conda create -n fiis-mvp python=3.11 -y
conda activate fiis-mvp

# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação
streamlit run app.py
