# Outputs — Análise Ad Hoc (Exploratória Sob Demanda)

Esta pasta contém os artefatos gerados pela execução de `scripts/analise_adhoc.py`.

| Arquivo | Formato | Para quem | Conteúdo |
|---------|---------|-----------|----------|
| `01_resumo_executivo.txt` | Texto | Diretoria / gestores | Diagnóstico das duas investigações: quais produtos caíram e se desconto gera valor — leitura em 2 minutos |
| `02_tabela_resultados.xlsx` | Excel | Analistas / planejamento | 3 abas: **resumo** (top quedas + correlação), **detalhe** (série mensal por produto), **parametros** (janelas temporais e método) |
| `03_grafico_principal.png` | Imagem | Apresentações executivas | Barras de delta de receita por produto (vermelho = queda, verde = crescimento) |
| `04_scatter_desconto_ticket.png` | Imagem | Pricing / planejamento | Scatter com linha de tendência mostrando relação desconto × ticket médio por cliente |

## Como Regenerar
```bash
# A partir da raiz do projeto
python generate_sample_data.py                        # gera dados sintéticos (se ainda não gerou)
python 03_analise_ad_hoc/scripts/analise_adhoc.py     # executa a análise e salva aqui
```

## Como Ler o Gráfico de Queda (Principal)

![Delta Receita](03_grafico_principal.png)

- **Barras vermelhas (negativas)** = produtos que perderam receita → investigar prioritariamente
- **Barras verdes (positivas)** = produtos que cresceram
- **Tamanho da barra** = impacto absoluto em R$
- A comparação é: média dos **2 meses mais recentes** vs média dos **3 meses anteriores**

**O que procurar:**
- O produto com a maior barra vermelha é o primeiro da fila para investigação
- Se TODOS os produtos estão no vermelho → problema macro (mercado, sazonalidade), não de produto específico
- Se apenas 1-2 produtos caíram forte → problema localizado (preço, estoque, concorrência)

## Como Ler o Scatter de Desconto × Ticket

![Scatter Desconto](04_scatter_desconto_ticket.png)

- Cada **ponto** = um cliente
- **Eixo X** = desconto médio que o cliente recebeu (%)
- **Eixo Y** = ticket médio do cliente (R$)
- **Linha tracejada vermelha** = tendência linear com coeficiente de correlação (r)

**O que procurar:**

| Padrão visual | Significado | Ação |
|--------------|------------|------|
| Nuvem descendente (↘) | Mais desconto → menor ticket | 🔴 Desconto pode estar destruindo valor. Revisar política |
| Nuvem ascendente (↗) | Mais desconto → maior ticket | 🟢 Desconto está gerando volume. Manter com controle |
| Nuvem dispersa (sem padrão) | Desconto não influencia ticket | 🟡 Dinheiro gasto em desconto pode estar sendo desperdiçado |

## Como Ler o Excel

Abra `02_tabela_resultados.xlsx`:

| Aba | O que contém | Como usar |
|-----|-------------|-----------|
| **resumo** | Top 10 produtos com maior queda (delta R$ e %) + insight | Resposta direta: "quais produtos estão em queda?" |
| **detalhe** | Série mensal completa por produto com delta calculado | Investigação: em qual mês exato a queda começou? Foi gradual ou abrupta? |
| **parametros** | Janelas comparadas, método (média, não soma), correlação Pearson, data | Rastreabilidade: qualquer pessoa reproduz a análise com os mesmos critérios |

## Diferença entre os Dois Gráficos

| Gráfico | Pergunta que responde | Granularidade |
|---------|----------------------|---------------|
| `03_grafico_principal.png` | Quais produtos caíram? | Por **produto** |
| `04_scatter_desconto_ticket.png` | Dar desconto funciona? | Por **cliente** |

São investigações independentes. Um produto pode estar em queda por motivos que não têm relação com desconto (sazonalidade, concorrência, problema operacional). O scatter complementa o diagnóstico, não substitui.

> **Nota:** Os arquivos nesta pasta são gerados com dados sintéticos determinísticos (`seed=42`). Em ambiente real, seriam gerados sob demanda quando uma pergunta de negócio surgir.
