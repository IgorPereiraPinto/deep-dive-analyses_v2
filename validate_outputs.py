"""
validate_outputs.py — Quality Gate do Portfólio
=================================================

OBJETIVO:
    Verificar se TODAS as análises geraram seus outputs obrigatórios.
    É o "teste de sanidade" final antes de commitar: se este script
    passa, o repositório está completo e funcional.

COMO EXECUTAR:
    python validate_outputs.py

OUTPUTS VERIFICADOS POR ANÁLISE:
    - 01_resumo_executivo.txt   (existe?)
    - 02_tabela_resultados.xlsx (existe?)
    - 03_grafico_principal.png  (existe?)

RETORNO:
    Exit code 0 = tudo OK (Quality Gate PASSED)
    Exit code 1 = algum output faltando (Quality Gate FAILED)

QUANDO USAR:
    1. Após rodar todas as 4 análises, antes de commitar
    2. Em CI/CD (GitHub Actions) para garantir integridade
    3. Após clonar o repo e gerar os dados pela primeira vez
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent

# ── Análises do projeto e seus diretórios ──
ANALYSES = [
    "01_analise_safra",
    "02_analise_pareto_abc",
    "03_analise_ad_hoc",
    "04_indicadores_vendas_mensal",
]

# ── Arquivos obrigatórios em cada pasta outputs/ ──
# São os 3 artefatos padronizados que toda análise deve gerar:
# TXT (resumo executivo), XLSX (tabela de resultados), PNG (gráfico principal)
REQUIRED_OUTPUT_FILES = [
    "01_resumo_executivo.txt",
    "02_tabela_resultados.xlsx",
    "03_grafico_principal.png",
]


@dataclass
class ValidationIssue:
    """Registra um problema encontrado na validação."""
    analysis: str
    missing_files: List[str]
    outputs_dir: Path


def _check_analysis_outputs(analysis_dir: Path) -> Tuple[bool, List[str]]:
    """
    Verifica se a pasta outputs/ de uma análise tem todos os arquivos.

    Retorna:
        (ok, missing): True se tudo existe, lista dos faltantes
    """
    outputs_dir = analysis_dir / "outputs"
    missing: List[str] = []

    if not outputs_dir.exists() or not outputs_dir.is_dir():
        return False, REQUIRED_OUTPUT_FILES.copy()

    for fname in REQUIRED_OUTPUT_FILES:
        if not (outputs_dir / fname).exists():
            missing.append(fname)

    return (len(missing) == 0), missing


def main() -> int:
    """
    Executa a validação completa e imprime o resultado.

    EXPLICAÇÃO PARA LEIGOS:
        Este script é como um "checklist de embarque" —
        antes de publicar o projeto, verificamos se todos
        os artefatos obrigatórios foram gerados corretamente.
    """
    print("\n" + "🔍" * 30)
    print("  QUALITY GATE — VALIDAÇÃO DE OUTPUTS")
    print("🔍" * 30)

    issues: List[ValidationIssue] = []

    for analysis in ANALYSES:
        analysis_dir = REPO_ROOT / analysis
        ok, missing = _check_analysis_outputs(analysis_dir)

        if ok:
            print(f"   ✅ {analysis}")
        else:
            print(f"   ❌ {analysis} — faltam {len(missing)} arquivo(s)")
            issues.append(
                ValidationIssue(
                    analysis=analysis,
                    missing_files=missing,
                    outputs_dir=analysis_dir / "outputs",
                )
            )

    # ── Resultado final ──
    if issues:
        print("\n" + "=" * 60)
        print("❌ QUALITY GATE FAILED — outputs obrigatórios ausentes.\n")
        for issue in issues:
            print(f"📂 {issue.analysis}")
            print(f"   Pasta: {issue.outputs_dir}")
            for mf in issue.missing_files:
                print(f"   • faltando: {mf}")
            print()
        print("Ação: gere os outputs faltantes executando cada análise:")
        print("   python generate_sample_data.py")
        for analysis in ANALYSES:
            script_name = analysis.split("_", 1)[1]
            print(f"   python {analysis}/scripts/analise_{script_name.split('_')[0]}.py")
        print()
        return 1

    print("\n" + "=" * 60)
    print("✅ QUALITY GATE PASSED — todos os outputs obrigatórios presentes.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
