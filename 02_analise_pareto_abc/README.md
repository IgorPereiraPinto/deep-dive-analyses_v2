# 02 — Análise Pareto / Curva ABC

## Pergunta de Negócio

> "Quais 20% dos clientes representam 80% da receita? Essa concentração está aumentando ou diminuindo? Quais clientes Classe B têm potencial de virar A? E quais clientes A estão em risco de saída?"

Toda operação comercial recorrente precisa saber **de quem depende**. Se 10 clientes respondem por 60% da receita, perder um deles é uma crise — e isso precisa estar mapeado antes que aconteça.

---

## Por Que Essa Análise É Importante

Um dashboard mostra que a receita total cresceu 5% no trimestre. Parece bom. Mas e se esse crescimento veio de **um único cliente grande** que aumentou o volume, enquanto 50 clientes pequenos saíram? A concentração aumentou, o risco cresceu, e o número "bonito" escondeu um problema estrutural.

A Análise de Pareto (Curva ABC) revela exatamente isso: como a receita está distribuída entre os clientes, e se essa distribuição está saudável ou perigosa.

### EXPLICAÇÃO PARA LEIGOS

O Princípio de Pareto (regra 80/20) diz que, em muitos fenômenos, 80% dos efeitos vêm de 20% das causas. Em vendas, isso se traduz em: poucos clientes geram a maior parte da receita.

A classificação ABC divide os clientes em 3 grupos:

- **Classe A** (0% a 80% da receita acumulada): os clientes mais valiosos. São poucos, mas representam a maior fatia. Precisam de atenção premium e plano de retenção dedicado.
- **Classe B** (80% a 95%): o "meio de campo". São candidatos naturais a crescimento — com upsell e cross-sell podem migrar para A.
- **Classe C** (95% a 100%): a "cauda longa". Muitos clientes, pouca receita individual. O custo de atendimento pode ser maior que o retorno.

---

## KPIs e Medidas Principais

| KPI | O que mede | Por que importa |
|-----|-----------|-----------------|
| **Receita total e participação Top 10** | Quanto os 10 maiores clientes representam no total | Se Top 10 > 50%, a carteira está perigosamente concentrada |
| **% acumulado de receita** | Curva de concentração (base do gráfico de Pareto) | Permite visualizar onde "corta" em 80% e 95% |
| **Participação da Classe A** | % de clientes vs % de receita da Classe A | O esperado é ~20% dos clientes gerando ~80% da receita |
| **Concentração por canal** | Distribuição ABC dentro de cada canal | Um canal pode ter concentração saudável enquanto outro está em risco |
| **Migração entre classes** | Clientes que mudaram de classe entre períodos | A→B/C = alerta de perda; B→A = oportunidade concretizada |

---

## Processo de ETL
```
SQL Server                    Power Query (Excel)              Python (Pandas)
    │                               │                               │
    ▼                               ▼                               ▼
 Query agrega receita         Padroniza colunas,            Ordena por receita desc,
 total por cliente com        valida consistência,          calcula % acumulado,
 ticket médio e meses ativos  trata tipos                   classifica A/B/C e gera outputs
```

### 1. Extração (SQL)

A query em `sql/` agrega o faturamento total por cliente, incluindo ticket médio, quantidade de meses ativo, número de produtos contratados e data do primeiro/último faturamento. Isso permite classificar e contextualizar cada cliente.

### 2. Transformação (Python)

O script ordena clientes do maior para o menor faturamento, calcula o percentual acumulado e aplica os thresholds:

| Classe | Faixa de receita acumulada | Significado |
|--------|---------------------------|-------------|
| **A** | 0% a 80% | Clientes que, juntos, formam os primeiros 80% da receita |
| **B** | 80% a 95% | Próximos 15% da receita |
| **C** | 95% a 100% | Últimos 5% da receita (cauda longa) |

### 3. Carga (Outputs)

Três artefatos padronizados na pasta `outputs/`.

---

## Como o Script Funciona (Passo a Passo)

| Passo | O que faz | Por quê |
|-------|----------|---------|
| **1. Carregar dados** | Lê a base de vendas e valida schema | Garantir integridade antes de classificar |
| **2. Agregar por cliente** | Soma receita total por `cliente_id` | Cada cliente precisa de um único valor para ranking |
| **3. Ordenar e acumular** | Ordena desc por receita, calcula `% acumulado` | Base para a classificação ABC e o gráfico de Pareto |
| **4. Classificar ABC** | Aplica thresholds 80% / 95% | Define a classe de cada cliente automaticamente |
| **5. Analisar concentração** | Calcula métricas de risco (Top 10, Gini) | Quantifica o nível de dependência da carteira |
| **6. Gerar visualizações** | Gráfico de Pareto com barras coloridas por classe + linha cumulativa | Comunicação visual imediata da concentração |
| **7. Validação** | % acumulado final = 100%, todo cliente tem 1 classe | Garante consistência lógica dos resultados |
| **8. Exportar** | TXT + XLSX + PNG na pasta `outputs/` | Entrega padronizada |

---

## Query SQL Documentada

A query em `sql/` retorna uma linha por cliente com:

- **Receita total**: soma de todo o faturamento no período
- **Ticket médio**: receita / número de transações
- **Meses ativo**: quantos meses distintos o cliente faturou
- **Quantidade de produtos**: diversificação do mix contratado
- **Primeiro e último faturamento**: indica tempo de relacionamento

> **Nota:** Neste portfólio, a extração é simulada com dados sintéticos. A query está pronta para execução direta em SQL Server.

---

## Exemplos de Output

### Gráfico de Pareto com Classificação ABC

![Gráfico Pareto](outputs/03_grafico_principal.png)

**Como ler este gráfico:**
- **Barras**: receita de cada cliente, ordenada do maior para o menor, coloridas por classe (A = azul, B = amarelo, C = cinza)
- **Linha vermelha**: % acumulado da receita — sobe rápido no início (poucos clientes grandes) e achata no final (muitos clientes pequenos)
- **Linha tracejada em 80%**: marca o corte da Classe A. Quanto mais à esquerda essa linha cruza, maior a concentração
- **Se os primeiros 10-15% dos clientes já cruzam 80%** → concentração alta → risco

### Tabela de Resultados (XLSX)

| Aba | Conteúdo | Uso |
|-----|----------|-----|
| **resumo** | Contagem de clientes, receita total e % por classe A/B/C | Visão rápida: "20% dos clientes geram 82% da receita" |
| **detalhe** | Lista completa de clientes com classe, receita, % individual, % acumulado | Identificar por nome quem são os clientes A e os B com potencial |
| **parametros** | Thresholds utilizados (80%/95%), período, data de geração | Rastreabilidade e reprodutibilidade |

---

## Insights Esperados

Com dados reais, um analista sênior buscaria:

1. **Se Classe A concentra >85% da receita com <15% dos clientes** → risco elevado. A perda de 2-3 clientes pode comprometer o resultado do trimestre. Recomendação: plano de retenção dedicado com gerente de conta exclusivo.

2. **Clientes B com múltiplos produtos** → candidatos naturais a upsell. Se um cliente B já compra Vale Alimentação e Refeição, oferecer Vale Combustível pode migrá-lo para A.

3. **Clientes A com ticket em queda** → alerta precoce de saída. Se o cliente A está reduzindo volume mês a mês, pode estar migrando para um concorrente gradualmente.

4. **Cauda longa (Classe C) com muitos clientes** → avaliar se o custo de atendimento compensa. Em alguns casos, vale automatizar o atendimento de C para liberar recursos para B (que tem potencial de crescimento).

5. **Concentração aumentando ao longo dos anos** → a carteira está ficando mais vulnerável, mesmo que a receita total cresça. É um sinal de que o crescimento depende de poucos, e a base ampla está encolhendo.

---

## Validações Realizadas

| Validação | Critério | Por que importa |
|-----------|----------|-----------------|
| % acumulado final | = 100% | Garante que todos os clientes foram incluídos na curva |
| Classe única | Todo cliente pertence a exatamente 1 classe | Sem duplicidade nem cliente sem classificação |
| Classe A ≈ 80% | Classe A deve conter ~80% da receita (±5%) | Confirmação de que os thresholds foram aplicados corretamente |
| Clientes Classe A | ≤ 30% do total de clientes | Se Classe A tem >30% dos clientes, os thresholds podem estar inadequados |
| Receita total | Soma do ranking = soma original | Nenhuma receita foi perdida ou duplicada no processo de agregação |

---

## Limitações e Próximos Passos

**O que esta análise NÃO cobre:**
- Não considera a **tendência** do cliente (está crescendo ou encolhendo?) — um cliente A hoje pode ser B amanhã
- A classificação é estática (foto do período) — não captura sazonalidade
- Não cruza com rentabilidade (um cliente A em receita pode ser C em margem)

**Evolução possível:**
- **Migração entre classes**: comparar ABC de 2024 vs 2025 — quais clientes subiram ou desceram?
- **ABC dinâmico**: recalcular trimestralmente e monitorar tendências
- **Cruzar com rentabilidade**: classificar por margem, não só receita — identificar clientes "grandes mas não rentáveis"
- **Segmentar por canal**: a concentração em Grandes Contas é naturalmente diferente de PME
- **Índice de Gini**: métrica única que resume o nível de concentração (0 = perfeita igualdade, 1 = total concentração)

---

## Execução
```bash
# A partir da raiz do projeto
python 02_analise_pareto_abc/scripts/analise_pareto.py
```

Para setup completo e geração de dados, consulte o [README na raiz do projeto](../README.md).
