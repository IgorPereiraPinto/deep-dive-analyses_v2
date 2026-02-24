"""
excel.py — Utilitários de exportação Excel para o portfólio
============================================================

Este módulo centraliza a lógica de criação de arquivos Excel
com o padrão do projeto: 3 abas (resumo, detalhe, parametros)
com formatação consistente.

Todas as 4 análises usam a função save_portfolio_table() para
gerar seus respectivos 02_tabela_resultados.xlsx.

COMO REAPROVEITAR:
    from src.utils.excel import save_portfolio_table

    save_portfolio_table(
        outputs_dir="caminho/para/outputs",
        filename="minha_tabela.xlsx",
        resumo=df_resumo,
        detalhe=df_detalhe,
        parametros=df_parametros,  # opcional
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd


def ensure_parent_dir(filepath: Union[str, Path]) -> Path:
    """
    Garante que o diretório pai do arquivo existe.

    Se o diretório não existir, cria automaticamente.
    Retorna o Path do arquivo (não do diretório).
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_excel_with_sheets(
    filepath: Union[str, Path],
    sheets: Dict[str, pd.DataFrame],
    *,
    index: bool = False,
    engine: str = "openpyxl",
    freeze_panes: Optional[tuple] = (1, 0),
) -> Path:
    """
    Salva um arquivo Excel com múltiplas abas.

    Parâmetros:
        filepath: caminho completo do arquivo .xlsx
        sheets: dicionário {nome_da_aba: DataFrame}
        index: se True, inclui o índice do DataFrame como coluna
        engine: engine do ExcelWriter (padrão: openpyxl)
        freeze_panes: posição de congelamento (linha, coluna)
                      padrão (1, 0) = congela a primeira linha (cabeçalho)

    Retorna:
        Path do arquivo criado

    EXPLICAÇÃO PARA LEIGOS:
        "Freeze panes" congela o cabeçalho da planilha — quando
        você rola para baixo, os nomes das colunas ficam visíveis.
        É um detalhe pequeno que faz diferença na usabilidade.
    """
    out_path = ensure_parent_dir(filepath)

    # Nomes de aba no Excel têm limite de 31 caracteres
    normalized_sheets = {}
    for name, df in sheets.items():
        normalized_sheets[str(name)[:31]] = df.copy()

    with pd.ExcelWriter(out_path, engine=engine) as writer:
        for sheet_name, df in normalized_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=index)

        # Aplicar freeze panes em todas as abas
        try:
            workbook = writer.book
            for sheet_name in normalized_sheets.keys():
                ws = workbook[sheet_name]
                if freeze_panes is not None:
                    row, col = freeze_panes
                    ws.freeze_panes = ws.cell(row=row + 1, column=col + 1)
        except Exception:
            # Se falhar (versão do openpyxl), segue sem congelar
            pass

    return out_path


def save_portfolio_table(
    outputs_dir: Union[str, Path],
    filename: str,
    resumo: pd.DataFrame,
    detalhe: pd.DataFrame,
    parametros: Optional[pd.DataFrame] = None,
    *,
    index: bool = False,
) -> Path:
    """
    Salva um Excel no padrão do portfólio (3 abas padronizadas).

    Este é o formato usado por TODAS as 4 análises do projeto:
    - Aba "resumo":     KPIs e métricas consolidadas
    - Aba "detalhe":    dados granulares para investigação
    - Aba "parametros": configurações usadas (rastreabilidade)

    Parâmetros:
        outputs_dir: pasta onde salvar o arquivo
        filename: nome do arquivo (ex: "02_tabela_resultados.xlsx")
        resumo: DataFrame com os KPIs principais
        detalhe: DataFrame com os dados detalhados
        parametros: DataFrame com os parâmetros usados (opcional)
        index: se True, inclui o índice como coluna

    Retorna:
        Path do arquivo criado
    """
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    sheets = {
        "resumo": resumo,
        "detalhe": detalhe,
    }
    if parametros is not None:
        sheets["parametros"] = parametros

    return save_excel_with_sheets(outputs_dir / filename, sheets, index=index)
