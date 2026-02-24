"""
analise_adhoc.py — Análise Ad Hoc (Exploratória Sob Demanda)
=============================================================

OBJETIVO:
    Responder duas investigações rápidas de performance comercial:
    (a) Quais produtos perderam receita recentemente?
    (b) Existe relação entre o nível de desconto e o ticket médio?

PERGUNTAS DE NEGÓCIO:
    "Quais produtos tiveram a maior queda nos últimos meses?"
    "Estamos dando desconto demais? Isso está gerando volume ou destruindo valor?"

COMO EXECUTAR:
    python 03_analise_ad_hoc/scripts/analise_adhoc.py

OUTPUTS GERADOS (em 03_analise_ad_hoc/outputs/):
    - 01_resumo_executivo.txt       → diagnóstico direto das duas investigações
    - 02_tabela_resultados.xlsx     → abas resumo / detalhe / parametros
    - 03_grafico_principal.png      → barras de delta de receita por produto
    - 04_scatter_desconto_ticket.png → scatter desconto × ticket médio

COMO REAPROVEITAR COM SEUS PRÓPRIOS DADOS:
    1. CAMINHO DOS DADOS (variável DATA_PATH):
       Troque pelo caminho do seu CSV ou Excel.

    2. COLUNAS OBRIGATÓRIAS:
       Para a Investigação (a):
       - "data"         → data da transação (YYYY-MM-DD)
       - "produto"      → nome do produto
       - "receita"      → valor faturado (> 0)

       Para a Investigação (b) — adicionar:
       - "cliente_id"   → identificador único do cliente
       - "desconto_pct" → percentual de desconto concedido (0 a 1)

       Se suas colunas têm nomes diferentes, renomeie no pd.read_csv().

    3. JANELAS TEMPORAIS (variáveis MESES_RECENTES e MESES_ANTERIORES):
       Padrão: compara os 2 meses mais recentes com os 3 anteriores.
       Altere conforme a necessidade do negócio.

DEPENDÊNCIAS:
    pip install pandas matplotlib openpyxl
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")  # Backend sem interface gráfica (servidores e CI/CD)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np

# ════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO (altere aqui para reaproveitar com seus dados)
# ════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.utils.excel import save_portfolio_table

# ── Caminhos ──
DATA_PATH = REPO_ROOT / "data/base_vendas_historica.csv"
OUTPUT_DIR = REPO_ROOT / "03_analise_ad_hoc/outputs"

# ── Colunas obrigatórias ──
REQUIRED_COLUMNS_QUEDA = {"data", "produto", "receita"}
REQUIRED_COLUMNS_CORR = {"cliente_id", "receita", "desconto_pct"}

# ── Janelas temporais para comparação ──
# "Comparar os N meses mais recentes com os M meses anteriores"
# Exemplo: MESES_RECENTES=2, MESES_ANTERIORES=3
#   Se o último mês é jan/2026, compara: dez/2025+jan/2026 vs set+out+nov/2025
MESES_RECENTES = 2
MESES_ANTERIORES = 3

# ── Visualização ──
TOP_N_QUEDA = 10  # Quantos produtos mostrar no resumo executivo


# ════════════════════════════════════════════════════════════════
# INVESTIGAÇÃO (A): QUEDA DE RECEITA POR PRODUTO
# ════════════════════════════════════════════════════════════════

def validate_input_queda(df: pd.DataFrame) -> None:
    """
    Validações para a investigação de queda de receita.

    EXPLICAÇÃO PARA LEIGOS:
        Antes de comparar "antes vs agora", precisamos garantir que:
        - Os dados têm as colunas certas (data, produto, receita)
        - Há meses suficientes para as duas janelas
        - Não há receita negativa distorcen
