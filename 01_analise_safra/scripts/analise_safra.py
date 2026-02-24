"""
analise_safra.py — Análise de Safra (Cohort / Coorte)
=====================================================

OBJETIVO:
    Avaliar a retenção de clientes agrupados pela safra (mês da primeira compra).
    A análise responde: "dos clientes que entraram em um determinado mês,
    quantos ainda estavam comprando 1, 2, 3... meses depois?"

PERGUNTA DE NEGÓCIO:
    "Quais coortes retêm melhor nos meses M1, M2 e M3?
     Onde há queda acelerada de retenção?"

COMO EXECUTAR:
    python 01_analise_safra/scripts/analise_safra.py

OUTPUTS GERADOS (em 01_analise_safra/outputs/):
    - 01_resumo_executivo.txt  → leitura rápida para gestores (2 min)
    - 02_tabela_resultados.xlsx → abas resumo / detalhe / parametros
    - 03_grafico_principal.png  → heatmap de retenção por coorte

COMO REAPROVEITAR COM SEUS PRÓPRIOS DADOS:
    Se você quer usar este script com dados reais, altere apenas estas variáveis:

    1. CAMINHO DOS DADOS (linha ~80):
       Troque: REPO_ROOT / "data/base_vendas_historica.csv"
       Por:    o caminho do seu arquivo (CSV ou Excel)

    2. NOMES DAS COLUNAS (linha ~85):
       O script espera 3 colunas mínimas:
       - "cliente_id"  → identificador único do cliente
       - "data"        → data da transação (formato YYYY-MM-DD)
       - "receita"     → valor faturado na transação (> 0)
       Se suas colunas têm nomes diferentes, renomeie no pd.read_csv()
       usando o parâmetro: .rename(columns={"seu_nome": "cliente_id"})

    3. PASTA DE SAÍDA (linha ~75):
       Troque OUTPUT_DIR se quiser salvar em outro local.

    O restante do código é genérico e funciona para qualquer base
    que tenha essas 3 colunas.

DEPENDÊNCIAS:
    pip install pandas matplotlib openpyxl
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")  # Backend sem interface gráfica (permite rodar em servidores)
import matplotlib.pyplot as plt
import pandas as pd

# ════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE CAMINHOS
# ════════════════════════════════════════════════════════════════
# REPO_ROOT aponta para a raiz do repositório (2 níveis acima deste script).
# Isso permite importar os módulos compartilhados de src/utils/.
#
# Estrutura esperada:
#   deep-dive-analyses_v2/          ← REPO_ROOT
#   ├── src/utils/excel.py
#   ├── data/base_vendas_historica.csv
#   └── 01_analise_safra/
#       └── scripts/analise_safra.py  ← você está aqui

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.utils.excel import save_portfolio_table

# ── Pasta onde os outputs serão salvos ──
# Se quiser mudar o destino, altere aqui:
OUTPUT_DIR = REPO_ROOT / "01_analise_safra/outputs"

# ── Caminho dos dados de entrada ──
# Para usar dados reais, troque este caminho:
DATA_PATH = REPO_ROOT / "data/base_vendas_historica.csv"

# ── Colunas obrigatórias na base de dados ──
# Se sua base tem nomes diferentes, ajuste o mapeamento no passo 1
REQUIRED_COLUMNS = {"cliente_id", "data", "receita"}


# ════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ════════════════════════════════════════════════════════════════

def validate_input(df: pd.DataFrame) -> None:
    """
    Validações de qualidade antes de iniciar a análise.

    EXPLICAÇÃO PARA LEIGOS:
        Antes de construir qualquer análise, um analista sênior
        SEMPRE valida os dados. É como um piloto checando os
        instrumentos antes de decolar. Se os dados estão errados,
        a análise inteira estará errada — e ninguém vai perceber
        até que uma decisão ruim seja tomada.
    """
    # 1. Verificar se todas as colunas necessárias existem
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    assert not missing_cols, (
        f"❌ Colunas ausentes na base: {missing_cols}\n"
        f"   Colunas encontradas: {list(df.columns)}\n"
        f"   Solução: renomeie suas colunas para: {REQUIRED_COLUMNS}"
    )

    # 2. Verificar se não há cliente_id nulo (cada transação precisa de dono)
    assert df["cliente_id"].notna().all(), (
        "❌ Existem transações sem cliente_id. Isso invalida a contagem de coorte."
    )

    # 3. Verificar se receita é sempre positiva (estornos devem ser tratados antes)
    assert df["receita"].gt(0).all(), (
        "❌ Existem registros com receita ≤ 0. Filtre estornos/cancelamentos antes."
    )

    print("   ✅ Validação de entrada OK")


def build_cohort_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Constrói a matriz de coorte: para cada safra (mês de entrada),
    calcula a % de clientes que continuaram comprando em cada mês subsequente.

    EXPLICAÇÃO PARA LEIGOS:
        Imagine que 100 clientes fizeram sua primeira compra em janeiro/2023.
        - Em fevereiro (M1), 72 deles compraram de novo → retenção = 72%
        - Em março (M2), 58 compraram → retenção = 58%
        - Em abril (M3), 51 compraram → retenção = 51%

        Fazemos isso para CADA mês de entrada, e colocamos tudo numa tabela.
        Isso é a "matriz de coorte".

    Retorna:
        cohort_counts: DataFrame com colunas [coorte, periodo_idx, clientes_ativos,
                       clientes_base, retencao]
        retention_matrix: DataFrame pivotado (linhas = coorte, colunas = período,
                         valores = % retenção)
    """
    # ── Passo A: Identificar a safra de cada cliente ──
    # A safra é o mês da PRIMEIRA compra. Usamos groupby + min para encontrar.
    # Exemplo: se o cliente 123 comprou em 2023-01-15, 2023-02-20, 2023-04-10,
    #          sua safra é "2023-01" (janeiro de 2023).
    first_purchase = (
        df.groupby("cliente_id")["data"]
        .min()                          # Menor data = primeira compra
        .dt.to_period("M")             # Converte para período mensal (2023-01)
        .astype(str)                   # Transforma em string para facilitar joins
        .rename("coorte")
    )

    df = df.join(first_purchase, on="cliente_id")

    # ── Passo B: Calcular o "mês de vida" de cada transação ──
    # periodo_idx = 0 significa "mês da primeira compra" (M0)
    # periodo_idx = 1 significa "1 mês depois da primeira compra" (M1)
    # periodo_idx = 2 significa "2 meses depois" (M2), e assim por diante.
    df["mes_compra"] = df["data"].dt.to_period("M")
    df["coorte_periodo"] = pd.PeriodIndex(df["coorte"], freq="M")
    df["periodo_idx"] = (df["mes_compra"] - df["coorte_periodo"]).apply(lambda x: x.n)

    # ── Passo C: Contar clientes únicos por coorte × período ──
    # Para cada combinação (safra, mês de vida), contamos quantos clientes
    # distintos fizeram pelo menos uma compra.
    cohort_counts = (
        df.groupby(["coorte", "periodo_idx"])["cliente_id"]
        .nunique()
        .reset_index(name="clientes_ativos")
    )

    # ── Passo D: Obter o tamanho base de cada coorte (M0) ──
    # M0 = quantos clientes entraram naquela safra. É o denominador da retenção.
    # Exemplo: se 100 clientes entraram em jan/2023, então clientes_base = 100.
    base_size = (
        cohort_counts[cohort_counts["periodo_idx"] == 0]
        [["coorte", "clientes_ativos"]]
        .rename(columns={"clientes_ativos": "clientes_base"})
    )

    # Validação: cada coorte deve aparecer exatamente 1 vez na base
    assert base_size["coorte"].is_unique, (
        "❌ Duplicidade de coorte na base de referência. Verifique os dados."
    )

    # ── Passo E: Calcular a retenção ──
    # retenção = clientes_ativos / clientes_base
    # Exemplo: 72 ativos / 100 na base = 0.72 = 72%
    cohort_counts = cohort_counts.merge(base_size, on="coorte", how="left")
    cohort_counts["retencao"] = (
        cohort_counts["clientes_ativos"] / cohort_counts["clientes_base"]
    ).round(4)

    # Validação: retenção deve estar entre 0% e 100%
    assert cohort_counts["retencao"].between(0, 1).all(), (
        "❌ Retenção fora do range [0, 1]. Verifique duplicidade de clientes."
    )

    # ── Passo F: Pivotar para formato de matriz ──
    # Linhas = coorte (safra), Colunas = período (M0, M1, M2...), Valores = retenção
    # Períodos não observados ficam como NaN (não como 0!) — uma safra recente
    # ainda não teve tempo de chegar ao M12, então NaN é correto, não é churn.
    retention_matrix = (
        cohort_counts
        .pivot(index="coorte", columns="periodo_idx", values="retencao")
        .sort_index()
    )

    return cohort_counts, retention_matrix


def build_summary(
    cohort_counts: pd.DataFrame,
    retention_matrix: pd.DataFrame,
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Monta as 3 abas do Excel: resumo, detalhe e parametros.

    EXPLICAÇÃO PARA LEIGOS:
        - Aba "resumo": visão rápida por coorte (quantos entraram, retenção M1/M2/M3, receita)
        - Aba "detalhe": a matriz completa de retenção para quem quer investigar a fundo
        - Aba "parametros": como os números foram gerados (rastreabilidade)
    """
    # ── Resumo: uma linha por coorte com os KPIs principais ──
    base_size = (
        cohort_counts[cohort_counts["periodo_idx"] == 0]
        [["coorte", "clientes_base"]]
    )
    revenue_by_cohort = df.groupby("coorte", as_index=False)["receita"].sum()
    resumo = base_size.merge(revenue_by_cohort, on="coorte", how="left")

    # Adicionar retenção nos marcos M1, M2 e M3 (os mais críticos)
    for m in [1, 2, 3]:
        col = (
            cohort_counts[cohort_counts["periodo_idx"] == m]
            [["coorte", "retencao"]]
            .rename(columns={"retencao": f"retencao_m{m}"})
        )
        resumo = resumo.merge(col, on="coorte", how="left")

    resumo["receita"] = resumo["receita"].fillna(0)
    resumo = resumo.sort_values("coorte")

    # ── Detalhe: a matriz de retenção completa ──
    detalhe = retention_matrix.reset_index()

    # ── Parametros: rastreabilidade da análise ──
    parametros = pd.DataFrame({
        "parametro": [
            "definicao_coorte",
            "janela_meses",
            "metrica_retencao",
            "data_geracao",
        ],
        "valor": [
            "Mês da primeira compra por cliente",
            str(int(df["periodo_idx"].max())),
            "clientes_ativos / clientes_base (M0)",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ],
    })

    return resumo, detalhe, parametros


def generate_heatmap(retention_matrix: pd.DataFrame, output_path: Path) -> None:
    """
    Gera o heatmap de retenção por coorte.

    COMO LER ESTE GRÁFICO:
        - Cada LINHA é uma safra (mês de entrada dos clientes)
        - Cada COLUNA é o mês de vida (M0 = entrada, M1 = 1 mês depois...)
        - A COR indica a % de retenção:
            → Azul escuro = alta retenção (bom)
            → Azul claro / branco = baixa retenção (alerta)
        - Procure por:
            → Linhas que clareiam rápido: safras com churn acelerado
            → Colunas que estabilizam: indica a base "hard core"
    """
    fig, ax = plt.subplots(figsize=(11, 6))

    im = ax.imshow(
        retention_matrix.values,
        aspect="auto",
        cmap="Blues",        # Escala de azul: mais escuro = mais retenção
        vmin=0, vmax=1,      # Fixar escala de 0% a 100% para comparabilidade
    )

    # Configurar eixos
    ax.set_xticks(range(retention_matrix.shape[1]))
    ax.set_xticklabels(retention_matrix.columns, fontsize=8)
    ax.set_yticks(range(retention_matrix.shape[0]))
    ax.set_yticklabels(retention_matrix.index, fontsize=8)

    ax.set_title("Retenção por Coorte × Mês de Vida", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Período desde a primeira compra (meses)")
    ax.set_ylabel("Coorte (mês de entrada)")

    fig.colorbar(im, ax=ax, label="Taxa de Retenção (0 = 0%  |  1 = 100%)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def generate_executive_summary(resumo: pd.DataFrame, output_path: Path) -> None:
    """
    Gera o resumo executivo em texto (TXT).

    EXPLICAÇÃO PARA LEIGOS:
        Este arquivo é feito para ser lido em 2 minutos por um diretor
        que quer saber: "o que está acontecendo com nossos clientes?"
        Sem gráficos, sem tabelas — só texto direto ao ponto.
    """
    # Filtrar apenas coortes que já tiveram tempo de chegar ao M1
    # (coortes muito recentes ainda não têm dado de retenção M1)
    maturadas_m1 = resumo[resumo["retencao_m1"].notna()]

    if maturadas_m1.empty:
        texto = ["⚠️ Nenhuma coorte com maturidade suficiente para avaliar retenção M1."]
    else:
        # Identificar as 3 melhores e 3 piores coortes em retenção M1
        top = maturadas_m1.sort_values("retencao_m1", ascending=False).head(3)["coorte"].tolist()
        low = maturadas_m1.sort_values("retencao_m1", ascending=True).head(3)["coorte"].tolist()

        # Calcular médias gerais para contexto
        avg_m1 = maturadas_m1["retencao_m1"].mean()
        avg_m2 = maturadas_m1["retencao_m2"].mean() if "retencao_m2" in maturadas_m1.columns else None
        avg_m3 = maturadas_m1["retencao_m3"].mean() if "retencao_m3" in maturadas_m1.columns else None

        texto = [
            "═" * 60,
            "RESUMO EXECUTIVO — Análise de Safra (Coorte)",
            "═" * 60,
            "",
            "RESULTADO GERAL:",
            f"  Retenção média em M1: {avg_m1:.1%}",
        ]

        if avg_m2 is not None:
            texto.append(f"  Retenção média em M2: {avg_m2:.1%}")
        if avg_m3 is not None:
            texto.append(f"  Retenção média em M3: {avg_m3:.1%}")

        texto.extend([
            "",
            "COORTES MAIS FORTES (maior retenção em M1):",
            f"  {', '.join(top)}",
            "",
            "COORTES MAIS FRACAS (menor retenção em M1):",
            f"  {', '.join(low)}",
            "",
            "AÇÕES RECOMENDADAS:",
            "  1. Reforçar onboarding e CRM no primeiro ciclo pós-aquisição",
            "     → Os 3 primeiros meses são críticos: se o cliente sobrevive",
            "       até M3, a probabilidade de permanência aumenta significativamente.",
            "  2. Investigar coortes fracas: o que aconteceu no mês de entrada?",
            "     → Mudança de preço? Campanha agressiva que trouxe clientes desqualificados?",
            "  3. Ativar campanhas de recompra para coortes com queda acentuada em M1",
            "     → Foco em win-back antes que completem 3 meses de inatividade (Lost).",
            "",
            "PRÓXIMOS PASSOS:",
            "  - Segmentar esta análise por canal de venda (PME vs Corporativo vs Grandes Contas)",
            "  - Cruzar com dados de NPS/satisfação para entender motivos de churn",
            "  - Incluir análise de sobrevivência (Kaplan-Meier) para estimativas com",
            "    intervalo de confiança",
            "═" * 60,
        ])

    output_path.write_text("\n".join(texto), encoding="utf-8")


# ════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Pipeline completo da Análise de Safra.

    Executa na ordem:
        1. Carregar e validar dados
        2. Construir matriz de coorte
        3. Montar tabelas de resumo
        4. Gerar heatmap de retenção
        5. Gerar resumo executivo
        6. Salvar outputs

    Todos os outputs são salvos em: 01_analise_safra/outputs/
    """
    print("\n" + "🔬" * 30)
    print("  ANÁLISE DE SAFRA (COORTE) — DEEP DIVE #01")
    print("🔬" * 30)

    # ── PASSO 1: Carregar dados ──────────────────────────────
    print("\n📂 Passo 1: Carregando dados...")
    df = pd.read_csv(DATA_PATH, parse_dates=["data"])
    print(f"   Registros carregados: {len(df):,}")
    print(f"   Período: {df['data'].min().strftime('%Y-%m')} a {df['data'].max().strftime('%Y-%m')}")
    print(f"   Clientes únicos: {df['cliente_id'].nunique():,}")

    # ── PASSO 2: Validar qualidade dos dados ─────────────────
    print("\n🔍 Passo 2: Validando dados...")
    validate_input(df)

    # ── PASSO 3: Construir matriz de coorte ──────────────────
    print("\n📊 Passo 3: Construindo matriz de coorte...")
    cohort_counts, retention_matrix = build_cohort_matrix(df)
    print(f"   Coortes identificadas: {retention_matrix.shape[0]}")
    print(f"   Período máximo de vida: M{retention_matrix.shape[1] - 1}")

    # ── PASSO 4: Montar tabelas de resumo ────────────────────
    print("\n📋 Passo 4: Montando tabelas de resumo...")
    resumo, detalhe, parametros = build_summary(cohort_counts, retention_matrix, df)
    print(f"   Linhas no resumo: {len(resumo)}")

    # ── PASSO 5: Gerar outputs ───────────────────────────────
    print("\n💾 Passo 5: Gerando outputs...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 5a. Excel com 3 abas padronizadas
    save_portfolio_table(
        OUTPUT_DIR,
        "02_tabela_resultados.xlsx",
        resumo=resumo,
        detalhe=detalhe,
        parametros=parametros,
    )
    print(f"   ✅ Excel: {OUTPUT_DIR / '02_tabela_resultados.xlsx'}")

    # 5b. Heatmap de retenção
    generate_heatmap(retention_matrix, OUTPUT_DIR / "03_grafico_principal.png")
    print(f"   ✅ Gráfico: {OUTPUT_DIR / '03_grafico_principal.png'}")

    # 5c. Resumo executivo em texto
    generate_executive_summary(resumo, OUTPUT_DIR / "01_resumo_executivo.txt")
    print(f"   ✅ Resumo: {OUTPUT_DIR / '01_resumo_executivo.txt'}")

    # ── RESULTADO FINAL ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ ANÁLISE DE SAFRA CONCLUÍDA!")
    print(f"   Outputs salvos em: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
