# FIIs – Ranking & Busca 📊

Aplicação web em **Streamlit** para análise educacional de Fundos de Investimento Imobiliário (FIIs).

> ⚠️ Projeto acadêmico / educacional.  
> Não constitui recomendação de investimento.

---

## ✨ Funcionalidades

- **Ranking inicial de FIIs** com:
  - Índice de risco (0–100)
  - Retorno 12m (preço + dividendos)
  - Volatilidade anual
  - Máx. drawdown (2 anos)
  - P/VP, segmento, etc.
- **Análise detalhada de um FII**:
  - Cards com principais métricas
  - Gráficos:
    - Preço (R$) – últimos 24 meses
    - Preço normalizado
    - Drawdown
    - Dividendos mensais (Yahoo)
  - Alternância entre:
    - Modo compacto (gráficos em abas)
    - Modo com todos os gráficos empilhados
- **Módulo “Minha carteira”**:
  - Seleção de FIIs que compõem a carteira
  - Cálculo de:
    - Quantidade de FIIs
    - Risco médio
    - Retorno médio 12m
  - Tabela apenas com os ativos selecionados

---

## 🧰 Tecnologias & Dependências

Linguagem e principais bibliotecas utilizadas:

- **Python 3.11+**
- **Streamlit** – interface web
- **pandas / numpy** – manipulação de dados
- **yfinance** – preços, volume e dividendos via Yahoo Finance
- **requests / requests-cache** – chamadas HTTP com cache
- **beautifulsoup4 / requests-html / pyppeteer** – scraping de páginas
- **pymongo** – acesso ao MongoDB Atlas (lista com todos os FIIs armazenada no banco de dados)
- **python-dotenv** – leitura de variáveis de ambiente

As versões mínimas estão em `requirements.txt`.

### Como executar no Windows

1. Baixe a pasta **`Projeto - Executar`**.
2. Extraia o conteúdo (pasta `Projeto/`).
3. Dentro da pasta extraída, dê dois cliques em `Executar.bat`.

O script vai criar/usar um ambiente virtual dentro da pasta, instalar as
dependências e abrir o app Streamlit no navegador.

### Como executar no Linux / macOS

Baixe a pasta **`Projeto - Executar`**, abra um terminal nela e execute:

```bash
pip install -r requirements.txt
streamlit run Script/core/app.py

