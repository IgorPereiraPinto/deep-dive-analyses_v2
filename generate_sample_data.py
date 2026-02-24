"""
generate_sample_data.py — Gerador de Dados Sintéticos Determinísticos
======================================================================

OBJETIVO:
    Gerar duas bases de dados sintéticas que simulam uma operadora de
    benefícios corporativos (tipo Pluxee, Sodexo, Alelo). Essas bases
    alimentam as 4 análises do portfólio Deep Dive Analyses.

POR QUE DADOS SINTÉTICOS?
    Em portfólio público, não é possível usar dados reais de empresas.
    Dados sintéticos determinísticos (seed=42) garantem:
    - Reprodutibilidade: qualquer pessoa gera exatamente os mesmos dados
    - Realismo: distribuições, sazonalidade e proporções simulam cenários reais
    - Segurança: nenhum dado confidencial é exposto

BASES GERADAS:
    1. base_vendas_historica.csv (em data/)
       → Tabela de fatos: uma linha por transação de faturamento
       → Colunas: data, mes_ref, cliente_id, produto, canal, regional,
         quantidade, receita, custo, desconto_pct

    2. forecast_mensal.csv (em data/)
       → Tabela de meta/forecast por canal × regional × produto × mês
       → Colunas: mes_ref, canal, regional, produto, meta_receita,
         forecast_receita

CONTEXTO DE NEGÓCIO SIMULADO:
    Empresa: operadora de benefícios corporativos
    Produtos recorrentes: Vale Alimentação, Vale Refeição, Vale Combustível
    Produtos complementares: Vale Transporte, Home Office, Gift,
                             Vale Cultura, Vale Saúde, Vale Mobilidade
    Canais: PME, Corporativo, Grandes Contas, Setor Público
    Regiões: Norte, Nordeste, Centro-Oeste, Sudeste, Sul

COMO EXECUTAR:
    python generate_sample_data.py

COMO REAPROVEITAR:
    Altere DataGenConfig para ajustar período, volume e seed.
    Altere as listas de produtos/canais para simular outro negócio.

DEPENDÊNCIAS:
    pip install pandas numpy
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DataGenConfig:
    """
    Parâmetros de geração dos dados sintéticos.

    Altere aqui para ajustar o volume e o período dos dados.
    O seed garante reprodutibilidade: mesmo seed = mesmos dados.
    """
    seed: int = 42
    start_date: str = "2021-01-01"
    end_date: str = "2026-01-31"
    n_rows: int = 120_000        # Total de transações
    n_clients: int = 5_000       # Base de clientes únicos


REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"

# ── Produtos ──
# Recorrentes: são a base do faturamento (maior frequência)
# Complementares: geram receita adicional (menor frequência)
PRODUTOS = np.array([
    "Vale Alimentação",    # Recorrente — maior volume
    "Vale Refeição",       # Recorrente
    "Vale Combustível",    # Recorrente
    "Vale Transporte",     # Complementar
    "Home Office",         # Complementar
    "Gift",                # Complementar
    "Vale Cultura",        # Complementar
    "Vale Saúde",          # Complementar
    "Vale Mobilidade",     # Complementar
])

# Probabilidade de cada produto ser comprado (simula mix real)
# Recorrentes têm probabilidade maior
PRODUTO_PROBS = np.array([
    0.22,   # Vale Alimentação — carro-chefe
    0.20,   # Vale Refeição — segundo maior
    0.15,   # Vale Combustível
    0.10,   # Vale Transporte
    0.08,   # Home Office
    0.07,   # Gift
    0.07,   # Vale Cultura
    0.06,   # Vale Saúde
    0.05,   # Vale Mobilidade
])

# ── Canais de venda ──
CANAIS = np.array(["PME", "Corporativo", "Grandes Contas", "Setor Público"])
CANAL_PROBS = np.array([0.40, 0.30, 0.18, 0.12])

# ── Regiões ──
REGIONAIS = np.array(["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"])
REGIONAL_PROBS = np.array([0.08, 0.18, 0.10, 0.42, 0.22])

# ── Preço base por produto (R$ por unidade/mês) ──
# Simula o valor médio que uma empresa paga por funcionário/mês
PRECO_BASE = {
    "Vale Alimentação":  620,
    "Vale Refeição":     580,
    "Vale Combustível":  450,
    "Vale Transporte":   320,
    "Home Office":       280,
    "Gift":              200,
    "Vale Cultura":      150,
    "Vale Saúde":        380,
    "Vale Mobilidade":   250,
}


# ════════════════════════════════════════════════════════════════
# VALIDAÇÕES
# ════════════════════════════════════════════════════════════════

def _validate_sales_schema(df: pd.DataFrame) -> None:
    """
    Valida o schema da base de vendas antes de salvar.

    Verifica:
    - Todas as colunas esperadas existem
    - Não há nulos
    - Não há duplicatas
    - Desconto está entre 0% e 25%
    - Valores numéricos são positivos
    """
    expected = {
        "data", "mes_ref", "cliente_id", "produto", "canal",
        "regional", "quantidade", "receita", "custo", "desconto_pct",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Schema incompleto em vendas: {sorted(missing)}")

    if df.isna().sum().sum() > 0:
        raise ValueError("Há nulos na base de vendas.")

    dup = df.duplicated().sum()
    if dup > 0:
        raise ValueError(f"Há {dup} linhas duplicadas na base de vendas.")

    if not df["desconto_pct"].between(0, 0.25).all():
        raise ValueError("desconto_pct fora do range [0, 0.25].")

    if (df[["quantidade", "receita", "custo"]] <= 0).any().any():
        raise ValueError("quantidade/receita/custo devem ser positivos.")


def _validate_forecast_schema(df: pd.DataFrame) -> None:
    """
    Valida o schema da base de forecast antes de salvar.

    Verifica:
    - Todas as colunas esperadas existem
    - Não há nulos
    - Não há duplicatas na chave composta
    """
    expected = {
        "mes_ref", "canal", "regional", "produto",
        "meta_receita", "forecast_receita",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Schema incompleto em forecast: {sorted(missing)}")

    if df.isna().sum().sum() > 0:
        raise ValueError("Há nulos na base de forecast.")

    if df.duplicated(["mes_ref", "canal", "regional", "produto"]).sum() > 0:
        raise ValueError("Há duplicidades na chave mes_ref/canal/regional/produto.")


# ════════════════════════════════════════════════════════════════
# GERAÇÃO DOS DADOS
# ════════════════════════════════════════════════════════════════

def generate_sample_data(config: DataGenConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Gera dados sintéticos determinísticos para vendas e forecast.

    EXPLICAÇÃO PARA LEIGOS:
        Esta função cria dados "falsos mas realistas" que imitam
        o comportamento de uma operadora de benefícios corporativos:
        - Sazonalidade: janeiro tem reajuste anual (+3%)
        - Mix de produtos: Vale Alimentação é o carro-chefe
        - Concentração: Sudeste tem 42% do volume (simula Brasil real)
        - Desconto: varia de 0% a 25% (política comercial típica)
        - Forecast: meta = realizado × fator aleatório (0.95 a 1.08)

    Parâmetros:
        config: DataGenConfig com seed, período, volume

    Retorna:
        (sales, forecast): tuple de DataFrames
    """
    rng = np.random.default_rng(config.seed)
    dates = pd.date_range(config.start_date, config.end_date, freq="D")

    # ── Gerar transações ──
    sampled_dates = rng.choice(dates, size=config.n_rows, replace=True)
    cliente_id = rng.integers(10_000, 10_000 + config.n_clients, size=config.n_rows)
    produto = rng.choice(PRODUTOS, size=config.n_rows, p=PRODUTO_PROBS)
    canal = rng.choice(CANAIS, size=config.n_rows, p=CANAL_PROBS)
    regional = rng.choice(REGIONAIS, size=config.n_rows, p=REGIONAL_PROBS)

    # ── Quantidade: funcionários atendidos por transação ──
    # PME: 1-10, Corporativo: 5-30, Grandes Contas: 20-80, Setor Público: 10-50
    quantidade = np.where(
        canal == "PME", rng.integers(1, 11, size=config.n_rows),
        np.where(
            canal == "Corporativo", rng.integers(5, 31, size=config.n_rows),
            np.where(
                canal == "Grandes Contas", rng.integers(20, 81, size=config.n_rows),
                rng.integers(10, 51, size=config.n_rows),  # Setor Público
            )
        )
    )

    # ── Preço base por produto ──
    preco_base = pd.Series(produto).map(PRECO_BASE).to_numpy(dtype=float)

    # ── Sazonalidade mensal ──
    # Janeiro: +3% (reajuste anual)
    # Novembro-Dezembro: +2% (efeito fim de ano / gift)
    # Fevereiro: -1% (mês curto)
    mes = pd.DatetimeIndex(sampled_dates).month.to_numpy()
    sazonal = np.ones(config.n_rows)
    sazonal[mes == 1] = 1.03    # Reajuste anual
    sazonal[mes == 2] = 0.99    # Mês curto
    sazonal[mes == 11] = 1.02   # Fim de ano
    sazonal[mes == 12] = 1.02   # Fim de ano

    # ── Desconto (0% a 25%) ──
    # Grandes Contas e Setor Público tendem a negociar mais desconto
    desconto_base = rng.uniform(0, 0.15, size=config.n_rows)
    desconto_extra = np.where(
        (canal == "Grandes Contas") | (canal == "Setor Público"),
        rng.uniform(0, 0.10, size=config.n_rows),
        0,
    )
    desconto_pct = np.clip(desconto_base + desconto_extra, 0, 0.25).round(4)

    # ── Receita = quantidade × preço × sazonalidade × (1 - desconto) × ruído ──
    ruido = rng.normal(1.0, 0.08, size=config.n_rows)
    receita = (quantidade * preco_base * sazonal * (1 - desconto_pct) * ruido).clip(min=30)

    # ── Custo = receita × fator de custo (55% a 82%) ──
    custo = (receita * rng.uniform(0.55, 0.82, size=config.n_rows)).clip(min=10)

    # ── Montar DataFrame de vendas ──
    sales = pd.DataFrame({
        "data": pd.to_datetime(sampled_dates),
        "cliente_id": cliente_id,
        "produto": produto,
        "canal": canal,
        "regional": regional,
        "quantidade": quantidade,
        "receita": receita.round(2),
        "custo": custo.round(2),
        "desconto_pct": desconto_pct,
    }).sort_values("data", ignore_index=True)

    sales["mes_ref"] = sales["data"].dt.to_period("M").astype(str)
    sales = sales[[
        "data", "mes_ref", "cliente_id", "produto", "canal",
        "regional", "quantidade", "receita", "custo", "desconto_pct",
    ]]

    # ── Gerar forecast (meta e forecast por dimensão × mês) ──
    # Meta = realizado × fator aleatório (0.95 a 1.08)
    # Simula meta definida pela área comercial com variação de ±5-8%
    monthly = (
        sales.groupby(["mes_ref", "canal", "regional", "produto"], as_index=False)["receita"]
        .sum()
        .rename(columns={"receita": "realizado"})
    )
    monthly["meta_receita"] = (
        monthly["realizado"] * rng.uniform(0.95, 1.08, size=len(monthly))
    ).round(2)
    monthly["forecast_receita"] = (
        monthly["meta_receita"] * rng.uniform(0.96, 1.04, size=len(monthly))
    ).round(2)

    forecast = monthly[[
        "mes_ref", "canal", "regional", "produto",
        "meta_receita", "forecast_receita",
    ]].copy()

    # ── Validar antes de retornar ──
    _validate_sales_schema(sales)
    _validate_forecast_schema(forecast)

    return sales, forecast


# ════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Gera as bases de dados e salva em data/.

    Execute este script UMA VEZ antes de rodar qualquer análise.
    As 4 análises leem os CSVs gerados aqui.
    """
    print("\n" + "📊" * 30)
    print("  GERADOR DE DADOS SINTÉTICOS — DEEP DIVE ANALYSES")
    print("📊" * 30)

    config = DataGenConfig()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n⚙️ Configuração:")
    print(f"   Seed: {config.seed}")
    print(f"   Período: {config.start_date} a {config.end_date}")
    print(f"   Transações: {config.n_rows:,}")
    print(f"   Clientes: {config.n_clients:,}")

    print("\n🔄 Gerando dados...")
    sales, forecast = generate_sample_data(config)

    sales_path = DATA_DIR / "base_vendas_historica.csv"
    forecast_path = DATA_DIR / "forecast_mensal.csv"

    sales.to_csv(sales_path, index=False, encoding="utf-8")
    forecast.to_csv(forecast_path, index=False, encoding="utf-8")

    # ── Resumo dos dados gerados ──
    print("\n✅ Dados gerados com sucesso!")
    print(f"\n📁 Base de vendas: {sales_path}")
    print(f"   Linhas: {len(sales):,}")
    print(f"   Clientes únicos: {sales['cliente_id'].nunique():,}")
    print(f"   Produtos: {sales['produto'].nunique()}")
    print(f"   Canais: {', '.join(sales['canal'].unique())}")
    print(f"   Período: {sales['mes_ref'].min()} a {sales['mes_ref'].max()}")
    print(f"   Receita total: R$ {sales['receita'].sum():,.2f}")

    print(f"\n📁 Base de forecast: {forecast_path}")
    print(f"   Linhas: {len(forecast):,}")
    print(f"   Meta total: R$ {forecast['meta_receita'].sum():,.2f}")

    print("\n" + "=" * 60)
    print("Próximo passo: execute cada análise individualmente:")
    print("   python 01_analise_safra/scripts/analise_safra.py")
    print("   python 02_analise_pareto_abc/scripts/analise_pareto.py")
    print("   python 03_analise_ad_hoc/scripts/analise_adhoc.py")
    print("   python 04_indicadores_vendas_mensal/scripts/analise_indicadores.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
