# Outputs — Análise de Safra (Cohort)

Esta pasta contém os 3 artefatos gerados pela execução de `scripts/analise_safra.py`.

| Arquivo | Formato | Para quem | Conteúdo |
|---------|---------|-----------|----------|
| `01_resumo_executivo.txt` | Texto | Diretoria / gestores | Insights, alertas e ações recomendadas — leitura em 2 minutos |
| `02_tabela_resultados.xlsx` | Excel | Analistas / planejamento | 3 abas: **resumo** (KPIs por coorte), **detalhe** (matriz de retenção completa), **parametros** (rastreabilidade) |
| `03_grafico_principal.png` | Imagem | Apresentações executivas | Heatmap de retenção — cada linha é uma safra, cada coluna é o mês de vida |

## Como Regenerar
```bash
# A partir da raiz do projeto
python generate_sample_data.py                      # gera dados sintéticos (se ainda não gerou)
python 01_analise_safra/scripts/analise_safra.py    # executa a análise e salva aqui
```

## Como Ler o Heatmap

![Heatmap Retenção](03_grafico_principal.png)

- **Linhas** = safra (mês de entrada dos clientes)
- **Colunas** = mês de vida (M0 = entrada, M1 = 1 mês depois...)
- **Cor escura** = alta retenção (bom) | **Cor clara** = baixa retenção (alerta)
- **Platô** = quando a cor estabiliza, indica a base "hard core" que tende a permanecer

## Como Ler o Excel

- Abra `02_tabela_resultados.xlsx`
- **Aba "resumo"**: compare `retencao_m1`, `retencao_m2`, `retencao_m3` entre coortes — quais turmas de clientes retêm melhor?
- **Aba "detalhe"**: a matriz completa — use para investigar em qual mês exato a retenção cai
- **Aba "parametros"**: registra como os números foram gerados (regras, janela temporal, data de execução)

> **Nota:** Os arquivos nesta pasta são gerados com dados sintéticos determinísticos (`seed=42`). Em ambiente real, seriam atualizados mensalmente com dados do SQL Server.
