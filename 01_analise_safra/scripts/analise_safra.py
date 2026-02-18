from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.utils.excel import save_portfolio_table


def main() -> None:
    df = pd.read_csv(REPO_ROOT / "data/base_vendas_historica.csv", parse_dates=["data"])
    assert df["cliente_id"].notna().all() and df["receita"].gt(0).all(), "Sanity check falhou para safra."
    expected_cols = {"cliente_id", "data", "receita"}
    assert expected_cols.issubset(df.columns), f"Schema inválido. Colunas ausentes: {expected_cols - set(df.columns)}"

    first_purchase = df.groupby("cliente_id")["data"].min().dt.to_period("M").astype(str).rename("coorte")
    df = df.join(first_purchase, on="cliente_id")
    df["mes_compra"] = df["data"].dt.to_period("M")
    df["coorte_periodo"] = pd.PeriodIndex(df["coorte"], freq="M")
    df["periodo_idx"] = (df["mes_compra"] - df["coorte_periodo"]).apply(lambda x: x.n)

    cohort_counts = (
        df.groupby(["coorte", "periodo_idx"])["cliente_id"].nunique().reset_index(name="clientes_ativos")
    )
    base_size = cohort_counts[cohort_counts["periodo_idx"] == 0][["coorte", "clientes_ativos"]].rename(columns={"clientes_ativos": "clientes_base"})
    assert base_size["coorte"].is_unique, "Duplicidade de coorte na base de referência."
    cohort_counts = cohort_counts.merge(base_size, on="coorte", how="left")
    cohort_counts["retencao"] = (cohort_counts["clientes_ativos"] / cohort_counts["clientes_base"]).round(4)
    assert cohort_counts["retencao"].between(0, 1).all(), "Retenção fora do range esperado [0, 1]."

    # Mantém períodos não observados como NaN para não interpretar maturação ausente como churn.
    retention_matrix = cohort_counts.pivot(index="coorte", columns="periodo_idx", values="retencao").sort_index()

    revenue_by_cohort = df.groupby("coorte", as_index=False)["receita"].sum()
    resumo = base_size.merge(revenue_by_cohort, on="coorte", how="left")
    for m in [1, 2, 3]:
        col = cohort_counts[cohort_counts["periodo_idx"] == m][["coorte", "retencao"]].rename(columns={"retencao": f"retencao_m{m}"})
        resumo = resumo.merge(col, on="coorte", how="left")
    resumo["receita"] = resumo["receita"].fillna(0)
    ultimo_mes_observado = df["mes_compra"].max()
    resumo["coorte_periodo"] = pd.PeriodIndex(resumo["coorte"], freq="M")
    resumo["maturada_m1"] = resumo["coorte_periodo"].le(ultimo_mes_observado - 1)
    # Se a coorte já maturou M1 e não houve recompra, a retenção correta é 0 (e não NaN).
    resumo.loc[resumo["maturada_m1"] & resumo["retencao_m1"].isna(), "retencao_m1"] = 0.0
    resumo = resumo.drop(columns=["coorte_periodo", "maturada_m1"])
    resumo = resumo.sort_values("coorte")

    detalhe = retention_matrix.reset_index()
    parametros = pd.DataFrame(
        {
            "parametro": ["definicao_coorte", "janela_meses", "data_geracao"],
            "valor": ["Mes da primeira compra por cliente", str(int(df["periodo_idx"].max())), datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        }
    )

    out_dir = REPO_ROOT / "01_analise_safra/outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    save_portfolio_table(out_dir, "02_tabela_resultados.xlsx", resumo=resumo, detalhe=detalhe, parametros=parametros)

    fig, ax = plt.subplots(figsize=(11, 6))
    im = ax.imshow(retention_matrix.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(retention_matrix.shape[1]))
    ax.set_xticklabels(retention_matrix.columns)
    ax.set_yticks(range(retention_matrix.shape[0]))
    ax.set_yticklabels(retention_matrix.index)
    ax.set_title("Retenção por Coorte x Mês")
    ax.set_xlabel("Período desde aquisição (mês)")
    ax.set_ylabel("Coorte")
    fig.colorbar(im, ax=ax, label="Retenção")
    fig.tight_layout()
    fig.savefig(out_dir / "03_grafico_principal.png", dpi=180)
    plt.close(fig)

    maturadas_m1 = resumo[resumo["retencao_m1"].notna()]
    top = maturadas_m1.sort_values("retencao_m1", ascending=False).head(3)["coorte"].tolist()
    low = maturadas_m1.sort_values("retencao_m1", ascending=True).head(3)["coorte"].tolist()
    texto = [
        "- Coortes mais fortes em M1: " + ", ".join(top),
        "- Coortes mais fracas em M1: " + ", ".join(low),
        "- Ação sugerida: reforçar onboarding e CRM no primeiro ciclo pós-aquisição.",
        "- Ação sugerida: ativar campanhas de recompra para coortes fracas.",
    ]
    (out_dir / "01_resumo_executivo.txt").write_text("\n".join(texto), encoding="utf-8")
    print("[OK] Análise 01 Safra concluída.")


if __name__ == "__main__":
    main()
