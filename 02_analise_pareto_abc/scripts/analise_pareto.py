"""
analise_pareto.py — Análise de Pareto / Curva ABC
==================================================

OBJETIVO:
    Classificar clientes por contribuição de receita usando o Princípio
    de Pareto (regra 80/20) e a Curva ABC. Identifica concentração de
    receita, riscos de dependência e oportunidades de crescimento.

PERGUNTA DE NEGÓCIO:
    "Quais 20% dos clientes representam 80% da receita?
     Qual o nível de dependência de poucos clientes?
     Quais clientes B têm potencial de virar A?"

COMO EXECUTAR:
    python 02_analise_pareto_abc/scripts/analise_pareto.py

OUTPUTS GERADOS (em 02_analise_pareto_abc/outputs/):
    - 01_resumo_executivo.txt  → riscos, concentração e ações recomendadas
    - 02_tabela_resultados.xlsx → abas resumo / detalhe / parametros
    - 03_grafico_principal.png  → gráfico de Pareto (barras + curva acumulada)

COMO REAPROVEITAR COM SEUS PRÓPRIOS DADOS:
    1. CAMINHO DOS DADOS (variável DATA_PATH):
       Troque pelo caminho do seu CSV ou Excel.

    2. COLUNAS OBRIGATÓRIAS:
       - "cliente_id"  → identificador único do cliente
       - "receita"     → valor faturado (≥ 0)
       Se suas colunas têm nomes diferentes, renomeie no pd.read_csv().

    3. THRESHOLDS ABC (variáveis ABC_THRESHOLD_A e ABC_THRESHOLD_B):
       Padrão: A até 80%, B até 95%, C o restante.
       Altere se sua empresa usa faixas diferentes.

    4. TOP N NO GRÁFICO (variável TOP_N_CHART):
       Padrão: mostra os 50 maiores clientes no Pareto.
       Aumente se sua carteira for muito grande.

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
OUTPUT_DIR = REPO_ROOT / "02_analise_pareto_abc/outputs"

# ── Colunas obrigatórias ──
REQUIRED_COLUMNS = {"cliente_id", "receita"}

# ── Thresholds da classificação ABC ──
# A = clientes que juntos formam os primeiros X% da receita
# B = próximos Y% da receita
# C = o restante
# Esses são os valores mais usados no mercado. Altere se necessário.
ABC_THRESHOLD_A = 0.80   # Classe A: 0% a 80% da receita acumulada
ABC_THRESHOLD_B = 0.95   # Classe B: 80% a 95% | Classe C: 95% a 100%

# ── Visualização ──
TOP_N_CHART = 50  # Quantos clientes mostrar no gráfico de Pareto

# ── Paleta de cores por classe ──
COLORS_ABC = {"A": "#2C3E50", "B": "#F39C12", "C": "#BDC3C7"}


# ════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ════════════════════════════════════════════════════════════════

def validate_input(df: pd.DataFrame) -> None:
    """
    Validações de qualidade antes de classificar.

    EXPLICAÇÃO PARA LEIGOS:
        Antes de dizer "20% dos clientes geram 80% da receita",
        precisamos ter certeza de que não há valores negativos
        (estornos) nem clientes duplicados distorcendo o ranking.
    """
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    assert not missing_cols, (
        f"❌ Colunas ausentes: {missing_cols}\n"
        f"   Encontradas: {list(df.columns)}\n"
        f"   Solução: renomeie suas colunas para: {REQUIRED_COLUMNS}"
    )

    assert df["receita"].ge(0).all(), (
        "❌ Existem registros com receita < 0. "
        "Filtre estornos/cancelamentos antes de rodar a análise."
    )

    assert df["cliente_id"].notna().all(), (
        "❌ Existem transações sem cliente_id."
    )

    print("   ✅ Validação de entrada OK")


def classify_abc(det: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica a classificação ABC baseada no % acumulado de receita.

    EXPLICAÇÃO PARA LEIGOS:
        Imagine que você tem 1.000 clientes. Colocamos todos em fila,
        do que mais compra ao que menos compra. Depois, vamos somando
        a receita de cada um:

        - O 1º cliente sozinho representa 5% da receita total
        - O 1º + 2º juntos = 9%
        - O 1º + 2º + 3º = 12%
        - ... e assim por diante até 100%

        Quando essa soma chega a 80%, paramos e dizemos:
        "Todos os clientes até aqui são Classe A".
        De 80% a 95% → Classe B. O restante → Classe C.

    Parâmetros:
        det: DataFrame com colunas [cliente_id, receita] já ordenado desc

    Retorna:
        DataFrame com colunas adicionais: pct_receita, pct_acumulado, classe_abc
    """
    # ── Calcular participação individual e acumulada ──
    receita_total = det["receita"].sum()
    det["pct_receita"] = det["receita"] / receita_total
    det["pct_acumulado"] = det["pct_receita"].cumsum()

    # ── Aplicar thresholds ──
    # pd.cut divide o % acumulado em faixas: [0→80%]=A, [80%→95%]=B, [95%→100%]=C
    det["classe_abc"] = pd.cut(
        det["pct_acumulado"],
        bins=[-0.001, ABC_THRESHOLD_A, ABC_THRESHOLD_B, 1.0],
        labels=["A", "B", "C"],
    )

    return det


def build_summary(det: pd.DataFrame) -> pd.DataFrame:
    """
    Monta o resumo executivo com os KPIs principais.

    EXPLICAÇÃO PARA LEIGOS:
        Este resumo responde em 4 números:
        - Quantos clientes temos no total?
        - Quanto faturamos no total?
        - Quanto os 10 maiores representam? (concentração extrema)
        - Quanto a Classe A inteira representa? (deve ser ~80%)
    """
    receita_total = det["receita"].sum()
    clientes_a = det[det["classe_abc"] == "A"]
    clientes_b = det[det["classe_abc"] == "B"]
    clientes_c = det[det["classe_abc"] == "C"]

    resumo = pd.DataFrame({
        "kpi": [
            "clientes_total",
            "receita_total",
            "top_10_participacao",
            "classe_A_clientes",
            "classe_A_participacao",
            "classe_A_pct_clientes",
            "classe_B_clientes",
            "classe_B_participacao",
            "classe_C_clientes",
            "classe_C_participacao",
        ],
        "valor": [
            int(det["cliente_id"].nunique()),
            float(receita_total),
            float(det.head(10)["receita"].sum() / receita_total),
            int(len(clientes_a)),
            float(clientes_a["receita"].sum() / receita_total),
            float(len(clientes_a) / len(det)),
            int(len(clientes_b)),
            float(clientes_b["receita"].sum() / receita_total),
            int(len(clientes_c)),
            float(clientes_c["receita"].sum() / receita_total),
        ],
        "descricao": [
            "Total de clientes na base",
            "Receita total no período (R$)",
            "% da receita concentrada nos 10 maiores clientes",
            "Quantidade de clientes Classe A",
            "% da receita gerada pela Classe A",
            "% dos clientes que são Classe A",
            "Quantidade de clientes Classe B",
            "% da receita gerada pela Classe B",
            "Quantidade de clientes Classe C",
            "% da receita gerada pela Classe C",
        ],
    })

    return resumo


def generate_pareto_chart(det: pd.DataFrame, output_path: Path) -> None:
    """
    Gera o gráfico de Pareto: barras de receita + curva acumulada.

    COMO LER ESTE GRÁFICO:
        - Eixo esquerdo (barras): receita de cada cliente, do maior ao menor
        - Eixo direito (linha vermelha): % acumulado da receita
        - Cores das barras: azul escuro = Classe A, amarelo = B, cinza = C
        - Linhas tracejadas: marcam 80% e 95% (cortes das classes)

        Se a linha vermelha sobe muito rápido e achata logo:
        → Poucos clientes dominam a receita → ALTA CONCENTRAÇÃO → RISCO

        Se a linha sobe gradualmente:
        → Receita bem distribuída → BAIXA CONCENTRAÇÃO → SAUDÁVEL
    """
    plot_df = det.head(TOP_N_CHART).copy().reset_index(drop=True)

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # ── Barras coloridas por classe ABC ──
    bar_colors = [COLORS_ABC.get(c, "#BDC3C7") for c in plot_df["classe_abc"]]
    ax1.bar(
        range(len(plot_df)),
        plot_df["receita"],
        color=bar_colors,
        edgecolor="white",
        linewidth=0.5,
    )
    ax1.set_ylabel("Receita (R$)", fontsize=11)
    ax1.set_xticks([])  # Muitos clientes — nomes não cabem no eixo
    ax1.set_xlabel(f"Clientes (Top {TOP_N_CHART}, ordenados por receita)", fontsize=11)

    # Formatar eixo Y em R$ com sufixos K/M
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"R$ {x/1e6:.1f}M" if x >= 1e6
        else f"R$ {x/1e3:.0f}K" if x >= 1e3
        else f"R$ {x:.0f}"
    ))

    # ── Linha de % acumulado (eixo secundário) ──
    ax2 = ax1.twinx()
    ax2.plot(
        range(len(plot_df)),
        plot_df["pct_acumulado"] * 100,
        color="#E74C3C",
        linewidth=2.5,
        marker="o",
        markersize=3,
        label="% Acumulado",
    )
    ax2.set_ylabel("% Acumulado da Receita", fontsize=11)
    ax2.set_ylim(0, 105)

    # ── Linhas de referência nos cortes ABC ──
    ax2.axhline(
        ABC_THRESHOLD_A * 100, color="gray", linestyle="--", linewidth=1,
        label=f"Corte A ({ABC_THRESHOLD_A:.0%})",
    )
    ax2.axhline(
        ABC_THRESHOLD_B * 100, color="gray", linestyle=":", linewidth=1,
        label=f"Corte B ({ABC_THRESHOLD_B:.0%})",
    )

    # ── Legenda das classes ──
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS_ABC["A"], label="Classe A (0–80%)"),
        Patch(facecolor=COLORS_ABC["B"], label="Classe B (80–95%)"),
        Patch(facecolor=COLORS_ABC["C"], label="Classe C (95–100%)"),
    ]
    ax1.legend(handles=legend_elements, loc="upper left", fontsize=9)
    ax2.legend(loc="center right", fontsize=9)

    ax1.set_title(
        f"Curva de Pareto — Receita por Cliente (Top {TOP_N_CHART})",
        fontsize=14, fontweight="bold", pad=15,
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def validate_output(det: pd.DataFrame) -> None:
    """
    Validações pós-classificação para garantir consistência.

    EXPLICAÇÃO PARA LEIGOS:
        Depois de classificar, conferimos se tudo bate:
        - O % acumulado do último cliente deve ser 100%
        - Todo cliente deve ter exatamente uma classe (A, B ou C)
        - A Classe A deve representar ~80% da receita (±5%)
    """
    # 1. % acumulado final deve ser ~100%
    assert abs(det["pct_acumulado"].iloc[-1] - 1.0) < 0.001, (
        "❌ % acumulado não chega a 100%. Verifique se há receita = 0."
    )

    # 2. Todo cliente tem exatamente 1 classe
    assert det["classe_abc"].notna().all(), (
        "❌ Existem clientes sem classificação ABC."
    )

    # 3. Classe A ≈ 80% da receita (tolerância de ±5%)
    pct_classe_a = det[det["classe_abc"] == "A"]["receita"].sum() / det["receita"].sum()
    assert 0.75 <= pct_classe_a <= 0.85, (
        f"⚠️ Classe A representa {pct_classe_a:.1%} da receita (esperado: ~80%). "
        f"Considere ajustar os thresholds."
    )

    print("   ✅ Validação de saída OK")


def generate_executive_summary(det: pd.DataFrame, resumo: pd.DataFrame, output_path: Path) -> None:
    """
    Gera o resumo executivo em texto (TXT).

    EXPLICAÇÃO PARA LEIGOS:
        Arquivo feito para ser lido em 2 minutos por um diretor.
        Responde: "qual o risco da nossa carteira?" e "o que fazer?"
    """
    receita_total = det["receita"].sum()
    top_10_pct = det.head(10)["receita"].sum() / receita_total
    clientes_a = det[det["classe_abc"] == "A"]
    clientes_b = det[det["classe_abc"] == "B"]
    pct_clientes_a = len(clientes_a) / len(det)
    pct_receita_a = clientes_a["receita"].sum() / receita_total

    # Classificar nível de concentração
    if top_10_pct > 0.50:
        nivel_risco = "🔴 CRÍTICO"
        risco_desc = "Os 10 maiores clientes sozinhos sustentam mais da metade da receita."
    elif top_10_pct > 0.35:
        nivel_risco = "🟡 ELEVADO"
        risco_desc = "Concentração significativa nos maiores clientes."
    else:
        nivel_risco = "🟢 MODERADO"
        risco_desc = "Receita relativamente bem distribuída."

    texto = [
        "═" * 60,
        "RESUMO EXECUTIVO — Análise de Pareto / Curva ABC",
        "═" * 60,
        "",
        "CONCENTRAÇÃO DE RECEITA:",
        f"  Nível de risco: {nivel_risco}",
        f"  {risco_desc}",
        "",
        f"  Top 10 clientes: {top_10_pct:.1%} da receita total",
        f"  Classe A: {pct_clientes_a:.1%} dos clientes geram {pct_receita_a:.1%} da receita",
        f"  Classe B: {len(clientes_b)} clientes com potencial de crescimento",
        "",
        "RISCOS IDENTIFICADOS:",
        f"  1. Dependência: perder 2-3 clientes Classe A pode comprometer",
        f"     {det.head(3)['receita'].sum() / receita_total:.1%} da receita total.",
        f"  2. Cauda longa: {len(det[det['classe_abc'] == 'C'])} clientes Classe C",
        f"     geram apenas {det[det['classe_abc'] == 'C']['receita'].sum() / receita_total:.1%} da receita.",
        "",
        "AÇÕES RECOMENDADAS:",
        "  1. CLASSE A — Retenção premium:",
        "     → Gerente de conta exclusivo, plano de retenção dedicado,",
        "       monitoramento mensal de ticket e satisfação.",
        "  2. CLASSE B — Desenvolvimento de carteira:",
        "     → Campanhas de upsell (aumentar ticket) e cross-sell (novos produtos).",
        "     → Clientes B com múltiplos produtos são candidatos naturais a migrar para A.",
        "  3. CLASSE C — Eficiência operacional:",
        "     → Automatizar atendimento para liberar recursos para Classe B.",
        "     → Avaliar se o custo de manutenção justifica a receita gerada.",
        "",
        "PRÓXIMOS PASSOS:",
        "  - Comparar ABC entre trimestres para detectar migração (A→B = alerta)",
        "  - Cruzar com rentabilidade: cliente grande em receita pode ser pequeno em margem",
        "  - Calcular Índice de Gini para monitorar evolução da concentração",
        "═" * 60,
        "",
        f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Thresholds: A até {ABC_THRESHOLD_A:.0%} | B até {ABC_THRESHOLD_B:.0%} | C restante",
    ]

    output_path.write_text("\n".join(texto), encoding="utf-8")


# ════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Pipeline completo da Análise de Pareto / Curva ABC.

    Executa na ordem:
        1. Carregar e validar dados
        2. Agregar receita por cliente
        3. Classificar ABC
        4. Montar resumo executivo
        5. Gerar gráfico de Pareto
        6. Validar consistência
        7. Exportar outputs
    """
    print("\n" + "🔬" * 30)
    print("  ANÁLISE DE PARETO / CURVA ABC — DEEP DIVE #02")
    print("🔬" * 30)

    # ── PASSO 1: Carregar dados ──────────────────────────────
    print("\n📂 Passo 1: Carregando dados...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Registros carregados: {len(df):,}")
    print(f"   Clientes únicos: {df['cliente_id'].nunique():,}")

    # ── PASSO 2: Validar qualidade ───────────────────────────
    print("\n🔍 Passo 2: Validando dados...")
    validate_input(df)

    # ── PASSO 3: Agregar receita por cliente ─────────────────
    # Cada cliente precisa de um único valor de receita para o ranking.
    # Somamos todas as transações do período.
    print("\n📊 Passo 3: Agregando receita por cliente...")
    det = (
        df.groupby("cliente_id", as_index=False)["receita"]
        .sum()
        .sort_values("receita", ascending=False)
        .reset_index(drop=True)
    )
    print(f"   Clientes para classificação: {len(det):,}")
    print(f"   Receita total: R$ {det['receita'].sum():,.2f}")
    print(f"   Maior cliente: R$ {det['receita'].iloc[0]:,.2f} "
          f"({det['receita'].iloc[0] / det['receita'].sum():.1%} do total)")

    # ── PASSO 4: Classificar ABC ─────────────────────────────
    print("\n🏷️ Passo 4: Classificando A/B/C...")
    det = classify_abc(det)

    for classe in ["A", "B", "C"]:
        subset = det[det["classe_abc"] == classe]
        print(f"   Classe {classe}: {len(subset):,} clientes "
              f"({len(subset)/len(det):.1%}) → "
              f"R$ {subset['receita'].sum():,.2f} "
              f"({subset['receita'].sum()/det['receita'].sum():.1%} da receita)")

    # ── PASSO 5: Montar resumo ───────────────────────────────
    print("\n📋 Passo 5: Montando resumo...")
    resumo = build_summary(det)

    # ── PASSO 6: Validar consistência ────────────────────────
    print("\n✔️ Passo 6: Validando classificação...")
    validate_output(det)

    # ── PASSO 7: Gerar outputs ───────────────────────────────
    print("\n💾 Passo 7: Gerando outputs...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 7a. Excel com 3 abas padronizadas
    parametros = pd.DataFrame({
        "parametro": [
            "regra_abc",
            "threshold_classe_a",
            "threshold_classe_b",
            "total_clientes",
            "periodo_dados",
            "data_geracao",
        ],
        "valor": [
            "A até 80%, B até 95%, C restante",
            str(ABC_THRESHOLD_A),
            str(ABC_THRESHOLD_B),
            str(len(det)),
            "Conforme base_vendas_historica.csv",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ],
    })

    save_portfolio_table(
        OUTPUT_DIR,
        "02_tabela_resultados.xlsx",
        resumo=resumo,
        detalhe=det,
        parametros=parametros,
    )
    print(f"   ✅ Excel: {OUTPUT_DIR / '02_tabela_resultados.xlsx'}")

    # 7b. Gráfico de Pareto
    generate_pareto_chart(det, OUTPUT_DIR / "03_grafico_principal.png")
    print(f"   ✅ Gráfico: {OUTPUT_DIR / '03_grafico_principal.png'}")

    # 7c. Resumo executivo em texto
    generate_executive_summary(det, resumo, OUTPUT_DIR / "01_resumo_executivo.txt")
    print(f"   ✅ Resumo: {OUTPUT_DIR / '01_resumo_executivo.txt'}")

    # 7d. CSV de resumo para visualização no GitHub
    resumo.to_csv(OUTPUT_DIR / "resumo_pareto_abc.csv", index=False, encoding="utf-8-sig")
    print(f"   ✅ CSV: {OUTPUT_DIR / 'resumo_pareto_abc.csv'}")

    # ── RESULTADO FINAL ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ ANÁLISE DE PARETO / CURVA ABC CONCLUÍDA!")
    print(f"   Outputs salvos em: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
