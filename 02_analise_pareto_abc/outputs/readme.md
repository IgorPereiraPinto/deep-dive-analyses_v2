# Outputs — Análise de Pareto / Curva ABC

Esta pasta contém os artefatos gerados pela execução de `scripts/analise_pareto.py`.

| Arquivo | Formato | Para quem | Conteúdo |
|---------|---------|-----------|----------|
| `01_resumo_executivo.txt` | Texto | Diretoria / gestores | Nível de concentração, riscos e ações por classe A/B/C — leitura em 2 minutos |
| `02_tabela_resultados.xlsx` | Excel | Analistas / planejamento | 3 abas: **resumo** (KPIs de concentração), **detalhe** (ranking completo de clientes com classe ABC), **parametros** (thresholds e rastreabilidade) |
| `03_grafico_principal.png` | Imagem | Apresentações executivas | Gráfico de Pareto com barras coloridas por classe + curva acumulada |
| `resumo_pareto_abc.csv` | CSV | Visualização no GitHub | Tabela de resumo renderizada nativamente pelo GitHub |

## Como Regenerar
```bash
# A partir da raiz do projeto
python generate_sample_data.py                           # gera dados sintéticos (se ainda não gerou)
python 02_analise_pareto_abc/scripts/analise_pareto.py   # executa a análise e salva aqui
```

## Como Ler o Gráfico de Pareto

![Gráfico Pareto](03_grafico_principal.png)

- **Barras** = receita de cada cliente, do maior ao menor
- **Cores**: azul escuro = Classe A | amarelo = Classe B | cinza = Classe C
- **Linha vermelha** = % acumulado da receita (eixo direito)
- **Linha tracejada em 80%** = corte da Classe A
- **Linha pontilhada em 95%** = corte da Classe B

**O que procurar:**
- Se a linha vermelha sobe muito rápido nos primeiros clientes → alta concentração → risco
- Se as barras azuis (Classe A) são poucas mas enormes → dependência de poucos clientes
- Se há muitas barras cinzas (Classe C) → cauda longa com baixo retorno individual

## Como Ler o Excel

Abra `02_tabela_resultados.xlsx`:

| Aba | O que contém | Como usar |
|-----|-------------|-----------|
| **resumo** | Total de clientes, receita total, participação Top 10, % por classe A/B/C | Responde em 30 segundos: "qual o nível de concentração da carteira?" |
| **detalhe** | Lista completa: cliente_id, receita, % individual, % acumulado, classe ABC | Identifique por nome: quem são os clientes A? Quais B têm potencial? Quais C custam mais do que geram? |
| **parametros** | Thresholds usados (80%/95%), total de clientes, data de geração | Rastreabilidade — qualquer pessoa consegue reproduzir exatamente esta classificação |

## Como Ler o Resumo Executivo (TXT)

O arquivo `01_resumo_executivo.txt` classifica automaticamente o nível de risco:

| Indicador | 🟢 Moderado | 🟡 Elevado | 🔴 Crítico |
|-----------|------------|-----------|-----------|
| Top 10 clientes | < 35% da receita | 35%–50% | > 50% |

Além do diagnóstico, o resumo inclui ações recomendadas por classe (A = retenção premium, B = desenvolvimento, C = eficiência) e próximos passos.

> **Nota:** Os arquivos nesta pasta são gerados com dados sintéticos determinísticos (`seed=42`). Em ambiente real, seriam atualizados mensalmente com dados do SQL Server.
