"""
analise_indicadores.py — Indicadores de Vendas Mensal (Real vs Meta)
=====================================================================

OBJETIVO:
    Comparar faturamento realizado com a meta/forecast mensal,
    localizar onde estão os gaps e decompor a causa raiz em
    efeitos de Volume, Preço e Mix.

PERGUNTAS DE NEGÓCIO:
    "Atingimos a meta do mês?"
    "Se não, onde exatamente ficou abaixo?"
    "Foi porque perdemos clientes (volume) ou porque o ticket caiu (preço)?"
    "Qual canal puxou o resultado para baixo?"

COMO EXECUTAR:
    python 04_indicadores_vendas_mensal/scripts/analise_indicadores.py

OUTPUTS GERADOS (em 04_indicadores_vendas_mensal/outputs/):
    - 01_resumo_executivo.txt       → diagnóstico com drivers e ações
    - 02_tabela_resultados.xlsx     → abas resumo / detalhe / parametros
    - 03_grafico_principal.png      → linhas Real vs Meta com gaps visuais

COMO REAPROVEITAR COM SEUS PRÓPRIOS DADOS:
    1. CAMINHO DOS DADOS (variáveis DATA_PATH_VENDAS e DATA_PATH_FORECAST):
       Troque pelos caminhos dos seus arquivos.

    2. COLUNAS OBRIGATÓRIAS NA BASE DE VENDAS:
       - "data"       → data da transação (YYYY-MM-DD)
       - "receita"    → valor faturado (> 0)
       - "canal"      → canal de venda
       - "regional"   → regional / região
       - "produto"    → nome do produto
       - "cliente_id" → identificador do cliente (para decomposição volume/preço)

    3. COLUNAS OBRIGATÓRIAS NO FORECAST:
       - "mes_ref"       → período no formato YYYY-MM
       - "canal"         → mesmo nome que na base de vendas
       - "regional"      → mesmo nome que na base de vendas
       - "produto"       → mesmo nome que na base de vendas
       - "meta_receita"  → valor esperado (R$)

    4. TOLERÂNCIA DE GAP (variável GAP_TOLERANCE):
       Padrão: ±2%. Altere conforme a política da empresa.

DEPENDÊNCIAS:
    pip install pandas matplotlib openpyxl numpy
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")  # Backend sem interface gráfica
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
DATA_PATH_VENDAS = REPO_ROOT / "data/base_vendas_historica.csv"
DATA_PATH_FORECAST = REPO_ROOT / "data/forecast_mensal.csv"
OUTPUT_DIR = REPO_ROOT / "04_indicadores_vendas_mensal/outputs"

# ── Colunas obrigatórias ──
REQUIRED_COLS_VENDAS = {"data", "receita", "canal", "regional", "produto", "cliente_id"}
REQUIRED_COLS_FORECAST = {"mes_ref", "canal", "regional", "produto", "meta_receita"}

# ── Tolerância para classificação de status ──
# Gap entre -2% e +2% = "Na Meta"
# Altere conforme a política da empresa (ex: ±3%, ±5%)
GAP_TOLERANCE = 0.02

# ── Dimensões para drill-down ──
DIMENSIONS = ["canal", "regional", "produto"]


# ════════════════════════════════════════════════════════════════
# VALIDAÇÕES
# ════════════════════════════════════════════════════════════════

def validate_inputs(vendas: pd.DataFrame, forecast: pd.DataFrame) -> None:
    """
    Validações de qualidade nas duas bases de entrada.

    EXPLICAÇÃO PARA LEIGOS:
        Antes de comparar real vs meta, precisamos garantir que:
        - As duas bases têm as colunas certas
        - A meta é positiva (meta zero ou negativa não faz sentido)
        - As chaves de join batem (se o forecast tem um canal que
          não existe nas vendas, a comparação fica furada)
    """
    # 1. Colunas obrigatórias
    missing_v = REQUIRED_COLS_VENDAS - set(vendas.columns)
    assert not missing_v, f"❌ Colunas ausentes em vendas: {missing_v}"

    missing_f = REQUIRED_COLS_FORECAST - set(forecast.columns)
    assert not missing_f, f"❌ Colunas ausentes no forecast: {missing_f}"

    # 2. Meta deve ser positiva
    assert forecast["meta_receita"].gt(0).all(), (
        "❌ Existem metas ≤ 0 no forecast. Meta zerada invalida o cálculo de gap %."
    )

    # 3. Verificar aderência de chaves
    canais_vendas = set(vendas["canal"].unique())
    canais_forecast = set(forecast["canal"].unique())
    canais_sobrando = canais_forecast - canais_vendas
    if canais_sobrando:
        print(f"   ⚠️ Canais no forecast sem dados de vendas: {canais_sobrando}")

    print("   ✅ Validação de entrada OK")


# ════════════════════════════════════════════════════════════════
# COMPARAÇÃO REAL VS FORECAST
# ════════════════════════════════════════════════════════════════

def build_monthly_summary(vendas: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida realizado vs meta por mês (visão macro).

    EXPLICAÇÃO PARA LEIGOS:
        Esta é a visão do "termômetro mensal":
        - Quanto faturamos este mês? (realizado)
        - Quanto era pra faturar? (meta)
        - Quanto faltou ou sobrou? (gap)
        - Estamos acima, na meta ou abaixo? (status)

        É o primeiro número que o diretor quer ver na reunião.
    """
    real_mensal = (
        vendas.groupby("mes_ref", as_index=False)["receita"]
        .sum()
        .rename(columns={"receita": "realizado"})
    )

    meta_mensal = (
        forecast.groupby("mes_ref", as_index=False)["meta_receita"]
        .sum()
        .rename(columns={"meta_receita": "meta"})
    )

    resumo = real_mensal.merge(meta_mensal, on="mes_ref", how="inner")
    resumo["gap"] = resumo["realizado"] - resumo["meta"]
    resumo["gap_pct"] = (resumo["gap"] / resumo["meta"]).round(4)

    # Classificar status com tolerância configurável
    resumo["status"] = resumo["gap_pct"].apply(classify_status)

    return resumo.sort_values("mes_ref")


def build_detail(vendas: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    """
    Detalha realizado vs meta por canal × regional × produto × mês.

    EXPLICAÇÃO PARA LEIGOS:
        Se o resumo diz "ficamos 5% abaixo da meta", o detalhe
        responde "foi o canal PME, na regional Sudeste, no produto
        Vale Combustível que puxou para baixo".

        É o drill-down que transforma diagnóstico em ação.
    """
    real_det = (
        vendas.groupby(["mes_ref"] + DIMENSIONS, as_index=False)["receita"]
        .sum()
        .rename(columns={"receita": "realizado"})
    )

    detalhe = real_det.merge(
        forecast,
        on=["mes_ref"] + DIMENSIONS,
        how="left",
    )

    detalhe["gap"] = detalhe["realizado"] - detalhe["meta_receita"]
    detalhe["gap_pct"] = (
        (detalhe["gap"] / detalhe["meta_receita"])
        .replace([float("inf"), -float("inf")], 0)
        .fillna(0)
    )
    detalhe["status"] = detalhe["gap_pct"].apply(classify_status)

    return detalhe


def classify_status(gap_pct: float) -> str:
    """
    Classifica o status com base no gap percentual.

    EXPLICAÇÃO PARA LEIGOS:
        Nem todo desvio é problema. Se ficamos 1% abaixo da meta,
        pode ser variação normal. Por isso usamos uma faixa de
        tolerância (padrão: ±2%):
        - Acima de +2%  → "Acima" (superou com folga)
        - Entre -2% e +2% → "Na Meta" (dentro do esperado)
        - Abaixo de -2% → "Abaixo" (requer investigação)
    """
    if gap_pct > GAP_TOLERANCE:
        return "Acima"
    elif gap_pct < -GAP_TOLERANCE:
        return "Abaixo"
    else:
        return "Na Meta"


# ════════════════════════════════════════════════════════════════
# DECOMPOSIÇÃO DE CAUSA RAIZ
# ════════════════════════════════════════════════════════════════

def decompose_root_cause(vendas: pd.DataFrame) -> pd.DataFrame:
    """
    Decompõe o gap em efeitos de Volume, Preço e Cruzado por canal.

    EXPLICAÇÃO PARA LEIGOS:
        Quando o faturamento cai, existem apenas 3 motivos possíveis:

        1. EFEITO VOLUME: perdemos clientes (ou ganhamos).
           Fórmula: (clientes_atual − clientes_anterior) × ticket_anterior
           → "Se o ticket tivesse ficado igual, quanto a mudança
              de clientes impactaria?"

        2. EFEITO PREÇO: os clientes estão pagando mais ou menos.
           Fórmula: clientes_anterior × (ticket_atual − ticket_anterior)
           → "Se a base de clientes fosse a mesma, quanto a mudança
              de ticket impactaria?"

        3. EFEITO CRUZADO: interação entre as duas mudanças.
           Fórmula: (Δ clientes) × (Δ ticket)
           → Residual matemático da decomposição.

        A soma dos 3 efeitos SEMPRE é igual ao gap total.
        Isso é uma propriedade matemática, não coincidência.

    Compara o MÊS MAIS RECENTE com o MÊS IMEDIATAMENTE ANTERIOR.
    """
    # Identificar os dois últimos meses
    meses = sorted(vendas["mes_ref"].unique())
    if len(meses) < 2:
        print("   ⚠️ Menos de 2 meses disponíveis — decomposição não é possível.")
        return pd.DataFrame()

    mes_atual = meses[-1]
    mes_anterior = meses[-2]

    # Agregar por canal: clientes únicos e receita total
    def agg_mes(df, mes):
        subset = df[df["mes_ref"] == mes]
        return (
            subset.groupby("canal", as_index=False)
            .agg(
                clientes=("cliente_id", "nunique"),
                receita=("receita", "sum"),
            )
            .assign(
                ticket_medio=lambda x: x["receita"] / x["clientes"]
            )
        )

    atual = agg_mes(vendas, mes_atual).rename(
        columns={"clientes": "clientes_atual", "receita": "receita_atual", "ticket_medio": "ticket_atual"}
    )
    anterior = agg_mes(vendas, mes_anterior).rename(
        columns={"clientes": "clientes_ant", "receita": "receita_ant", "ticket_medio": "ticket_ant"}
    )

    # Juntar os dois meses
    decomp = anterior.merge(atual, on="canal", how="outer").fillna(0)

    # Calcular os 3 efeitos
    decomp["delta_clientes"] = decomp["clientes_atual"] - decomp["clientes_ant"]
    decomp["delta_ticket"] = decomp["ticket_atual"] - decomp["ticket_ant"]

    decomp["efeito_volume"] = decomp["delta_clientes"] * decomp["ticket_ant"]
    decomp["efeito_preco"] = decomp["clientes_ant"] * decomp["delta_ticket"]
    decomp["efeito_cruzado"] = decomp["delta_clientes"] * decomp["delta_ticket"]

    decomp["gap_total"] = decomp["receita_atual"] - decomp["receita_ant"]

    # Validação: soma dos efeitos ≈ gap total
    decomp["check"] = (
        decomp["efeito_volume"] + decomp["efeito_preco"] + decomp["efeito_cruzado"]
    )
    diff = (decomp["gap_total"] - decomp["check"]).abs()
    assert diff.max() < 0.01, (
        f"❌ Decomposição não fecha: diferença máxima = R$ {diff.max():.4f}"
    )

    decomp["mes_atual"] = mes_atual
    decomp["mes_anterior"] = mes_anterior

    return decomp


# ════════════════════════════════════════════════════════════════
# VISUALIZAÇÕES
# ════════════════════════════════════════════════════════════════

def generate_chart_real_vs_meta(resumo: pd.DataFrame, output_path: Path) -> None:
    """
    Gráfico de linhas: Realizado vs Meta com gaps visuais.

    COMO LER ESTE GRÁFICO:
        - Linha azul = realizado (o que efetivamente faturamos)
        - Linha tracejada cinza = meta / forecast
        - Linhas verticais verdes = meses acima da meta
        - Linhas verticais vermelhas = meses abaixo da meta
        - Quanto mais longa a linha vertical, maior o gap
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(resumo))

    # Linhas de realizado e meta
    ax.plot(x, resumo["realizado"], marker="o", markersize=6,
            color="#2C3E50", linewidth=2.5, label="Realizado", zorder=3)
    ax.plot(x, resumo["meta"], marker="s", markersize=5,
            color="#95A5A6", linewidth=2, linestyle="--", label="Meta / Forecast", zorder=2)

    # Linhas verticais de gap (verde = acima, vermelho = abaixo)
    for i, row in resumo.iterrows():
        idx = list(resumo.index).index(i)
        color = "#27AE60" if row["gap"] >= 0 else "#E74C3C"
        ax.vlines(idx, row["meta"], row["realizado"],
                  colors=color, linewidth=3, alpha=0.6, zorder=1)

    # Formatar eixos
    ax.set_xticks(list(x))
    ax.set_xticklabels(resumo["mes_ref"], rotation=45, ha="right", fontsize=9)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda val, _: f"R$ {val/1e6:.1f}M" if val >= 1e6
        else f"R$ {val/1e3:.0f}K" if val >= 1e3
        else f"R$ {val:.0f}"
    ))

    ax.set_title("Realizado vs Meta — Evolução Mensal",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Faturamento (R$)", fontsize=11)
    ax.set_xlabel("Mês", fontsize=11)
    ax.legend(fontsize=11, loc="upper left")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


# ════════════════════════════════════════════════════════════════
# RESUMO EXECUTIVO
# ════════════════════════════════════════════════════════════════

def generate_executive_summary(
    resumo: pd.DataFrame,
    detalhe: pd.DataFrame,
    decomp: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Gera narrativa executiva automática.

    EXPLICAÇÃO PARA LEIGOS:
        Este é o "e-mail que o analista mandaria para o diretor"
        após a reunião de resultado. Responde:
        - Atingimos a meta?
        - Qual o principal detrator?
        - Qual o principal destaque positivo?
        - Qual a causa raiz (volume ou preço)?
        - O que fazer a respeito?
    """
    # Métricas do último mês
    ultimo = resumo.iloc[-1]
    meses_acima = len(resumo[resumo["status"] == "Acima"])
    meses_abaixo = len(resumo[resumo["status"] == "Abaixo"])
    meses_na_meta = len(resumo[resumo["status"] == "Na Meta"])

    # Drivers de gap por produto (acumulado)
    drivers_produto = (
        detalhe.groupby("produto", as_index=False)["gap"]
        .sum()
        .sort_values("gap")
    )
    top_negativo = drivers_produto.iloc[0]
    top_positivo = drivers_produto.iloc[-1]

    # Drivers de gap por canal (acumulado)
    drivers_canal = (
        detalhe.groupby("canal", as_index=False)["gap"]
        .sum()
        .sort_values("gap")
    )

    texto = [
        "═" * 60,
        "RESUMO EXECUTIVO — Indicadores de Vendas Mensal",
        "═" * 60,
        "",
        f"RESULTADO DO ÚLTIMO MÊS ({ultimo['mes_ref']}):",
        f"  Realizado: R$ {ultimo['realizado']:,.0f}",
        f"  Meta:      R$ {ultimo['meta']:,.0f}",
        f"  Gap:       R$ {ultimo['gap']:+,.0f} ({ultimo['gap_pct']:+.1%})",
        f"  Status:    {'🟢' if ultimo['status'] == 'Acima' else '🟡' if ultimo['status'] == 'Na Meta' else '🔴'} {ultimo['status']}",
        "",
        "VISÃO DO PERÍODO:",
        f"  Meses acima da meta:  {meses_acima}",
        f"  Meses na meta:        {meses_na_meta}",
        f"  Meses abaixo da meta: {meses_abaixo}",
        "",
        "─" * 60,
        "",
        "DRIVERS DE GAP (por produto, acumulado no período):",
        f"  🔴 Maior detrator: {top_negativo['produto']}",
        f"     Gap acumulado: R$ {top_negativo['gap']:+,.0f}",
        f"  🟢 Melhor performer: {top_positivo['produto']}",
        f"     Gap acumulado: R$ {top_positivo['gap']:+,.0f}",
        "",
        "  Por canal (acumulado):",
    ]

    for _, row in drivers_canal.iterrows():
        emoji = "🔴" if row["gap"] < 0 else "🟢"
        texto.append(f"     {emoji} {row['canal']}: R$ {row['gap']:+,.0f}")

    texto.append("")

    # Decomposição de causa raiz (se disponível)
    if not decomp.empty:
        texto.extend([
            "─" * 60,
            "",
            f"DECOMPOSIÇÃO DE CAUSA RAIZ ({decomp.iloc[0]['mes_anterior']} → {decomp.iloc[0]['mes_atual']}):",
        ])

        vol_total = decomp["efeito_volume"].sum()
        preco_total = decomp["efeito_preco"].sum()
        cruz_total = decomp["efeito_cruzado"].sum()
        gap_total = decomp["gap_total"].sum()

        texto.extend([
            f"  Gap Total:      R$ {gap_total:+,.0f}",
            f"  Efeito Volume:  R$ {vol_total:+,.0f} "
            f"({abs(vol_total)/abs(gap_total)*100 if gap_total != 0 else 0:.0f}% do gap)",
            f"  Efeito Preço:   R$ {preco_total:+,.0f} "
            f"({abs(preco_total)/abs(gap_total)*100 if gap_total != 0 else 0:.0f}% do gap)",
            f"  Efeito Cruzado: R$ {cruz_total:+,.0f}",
            "",
        ])

        # Diagnóstico automático baseado no efeito dominante
        if abs(vol_total) > abs(preco_total):
            texto.extend([
                "  DIAGNÓSTICO: Gap dominado por EFEITO VOLUME.",
                "  → O problema principal é perda (ou ganho) de clientes ativos.",
                "  → Ação: alinhar pipeline de aquisição e estratégia de retenção.",
            ])
        else:
            texto.extend([
                "  DIAGNÓSTICO: Gap dominado por EFEITO PREÇO.",
                "  → Os clientes estão, mas gastam diferente do esperado.",
                "  → Ação: revisar política de pricing, renegociações e downgrades.",
            ])

        texto.append("")

        # Detalhamento por canal
        texto.append("  Por canal:")
        for _, row in decomp.iterrows():
            texto.append(
                f"     {row['canal']}: "
                f"Volume R$ {row['efeito_volume']:+,.0f} | "
                f"Preço R$ {row['efeito_preco']:+,.0f} | "
                f"Cruzado R$ {row['efeito_cruzado']:+,.0f}"
            )

    texto.extend([
        "",
        "─" * 60,
        "",
        "AÇÕES RECOMENDADAS:",
        f"  1. {top_negativo['produto']}: investigar causa da queda.",
        "     → Decompor em volume vs preço no nível de cliente.",
        "     → Verificar se houve mudança de preço, perda de contratos ou sazonalidade.",
        f"  2. {top_positivo['produto']}: capturar a oportunidade.",
        "     → Identificar o que está funcionando e replicar para outros produtos.",
        "  3. Canais abaixo da meta: alinhar plano de ação com gerentes.",
        "     → Cada canal deve ter meta e acompanhamento individualizados.",
        "",
        "PRÓXIMOS PASSOS:",
        "  - Drill-down até nível de gerência/vendedor nos canais deficitários",
        "  - Incluir forecast dinâmico (média móvel ou Prophet) para metas mais realistas",
        "  - Integrar com análise de safra (01) para cruzar gap com churn",
        "  - Adicionar intervalo de confiança para reduzir falsos alertas",
        "═" * 60,
        "",
        f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Tolerância de gap: ±{GAP_TOLERANCE:.0%}",
    ])

    output_path.write_text("\n".join(texto), encoding="utf-8")


# ════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Pipeline completo da Análise de Indicadores (Real vs Meta).

    Executa na ordem:
        1. Carregar e validar vendas + forecast
        2. Consolidar visão mensal (macro)
        3. Detalhar por canal × regional × produto
        4. Decompor causa raiz (volume / preço / cruzado)
        5. Gerar visualizações e narrativa
        6. Exportar outputs
    """
    print("\n" + "🔬" * 30)
    print("  INDICADORES DE VENDAS MENSAL — DEEP DIVE #04")
    print("🔬" * 30)

    # ── PASSO 1: Carregar dados ──────────────────────────────
    print("\n📂 Passo 1: Carregando dados...")
    vendas = pd.read_csv(DATA_PATH_VENDAS, parse_dates=["data"])
    forecast = pd.read_csv(DATA_PATH_FORECAST)

    vendas["mes_ref"] = vendas["data"].dt.to_period("M").astype(str)

    print(f"   Vendas: {len(vendas):,} registros")
    print(f"   Período: {vendas['mes_ref'].min()} a {vendas['mes_ref'].max()}")
    print(f"   Forecast: {len(forecast):,} linhas")

    # ── PASSO 2: Validar ─────────────────────────────────────
    print("\n🔍 Passo 2: Validando dados...")
    validate_inputs(vendas, forecast)

    # ── PASSO 3: Consolidar visão mensal ─────────────────────
    print("\n📊 Passo 3: Consolidando Real vs Meta por mês...")
    resumo = build_monthly_summary(vendas, forecast)

    meses_acima = len(resumo[resumo["status"] == "Acima"])
    meses_abaixo = len(resumo[resumo["status"] == "Abaixo"])
    print(f"   Meses analisados: {len(resumo)}")
    print(f"   Acima da meta: {meses_acima} | Abaixo: {meses_abaixo}")

    ultimo = resumo.iloc[-1]
    print(f"   Último mês ({ultimo['mes_ref']}): "
          f"R$ {ultimo['gap']:+,.0f} ({ultimo['gap_pct']:+.1%}) → {ultimo['status']}")

    # ── PASSO 4: Detalhar por dimensão ───────────────────────
    print("\n🔎 Passo 4: Detalhando por canal × regional × produto...")
    detalhe = build_detail(vendas, forecast)
    abaixo_count = len(detalhe[detalhe["status"] == "Abaixo"])
    print(f"   Combinações analisadas: {len(detalhe):,}")
    print(f"   Abaixo da meta: {abaixo_count}")

    # ── PASSO 5: Decompor causa raiz ─────────────────────────
    print("\n🧬 Passo 5: Decomposição de causa raiz (último mês vs anterior)...")
    decomp = decompose_root_cause(vendas)
    if not decomp.empty:
        vol_total = decomp["efeito_volume"].sum()
        preco_total = decomp["efeito_preco"].sum()
        gap_total = decomp["gap_total"].sum()
        dominante = "VOLUME" if abs(vol_total) > abs(preco_total) else "PREÇO"
        print(f"   Gap total: R$ {gap_total:+,.0f}")
        print(f"   Efeito Volume: R$ {vol_total:+,.0f}")
        print(f"   Efeito Preço:  R$ {preco_total:+,.0f}")
        print(f"   Efeito dominante: {dominante}")
        print("   ✅ Decomposição validada (soma dos efeitos = gap total)")

    # ── PASSO 6: Gerar outputs ───────────────────────────────
    print("\n💾 Passo 6: Gerando outputs...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 6a. Excel com 3 abas
    parametros = pd.DataFrame({
        "parametro": [
            "granularidade",
            "fonte_meta",
            "tolerancia_gap",
            "metodo_decomposicao",
            "data_geracao",
        ],
        "valor": [
            "mes_ref × canal × regional × produto",
            str(DATA_PATH_FORECAST.name),
            f"±{GAP_TOLERANCE:.0%}",
            "Efeito Volume + Efeito Preço + Efeito Cruzado (aditivo)",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ],
    })

    save_portfolio_table(
        OUTPUT_DIR,
        "02_tabela_resultados.xlsx",
        resumo=resumo,
        detalhe=detalhe,
        parametros=parametros,
    )
    print(f"   ✅ Excel: {OUTPUT_DIR / '02_tabela_resultados.xlsx'}")

    # 6b. Gráfico Real vs Meta
    generate_chart_real_vs_meta(resumo, OUTPUT_DIR / "03_grafico_principal.png")
    print(f"   ✅ Gráfico: {OUTPUT_DIR / '03_grafico_principal.png'}")

    # 6c. Resumo executivo com narrativa
    generate_executive_summary(resumo, detalhe, decomp, OUTPUT_DIR / "01_resumo_executivo.txt")
    print(f"   ✅ Resumo: {OUTPUT_DIR / '01_resumo_executivo.txt'}")

    # 6d. CSV de resumo para visualização no GitHub
    resumo.to_csv(OUTPUT_DIR / "resumo_real_vs_forecast.csv", index=False, encoding="utf-8-sig")
    print(f"   ✅ CSV: {OUTPUT_DIR / 'resumo_real_vs_forecast.csv'}")

    # ── RESULTADO FINAL ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ ANÁLISE DE INDICADORES CONCLUÍDA!")
    print(f"   Outputs salvos em: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
