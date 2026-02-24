# 01 — Análise de Safra (Cohort)

## Pergunta de Negócio

> "Dos clientes que começaram a faturar em janeiro/2021, quantos ainda estão ativos hoje? Quanto tempo leva em média até um cliente se tornar Lost? Existe diferença significativa entre canais? E qual a taxa de reativação?"

Essa é uma das perguntas mais importantes para qualquer operação comercial recorrente. Saber **quando** e **por que** os clientes saem permite agir antes que a perda se concretize.

---

## Por Que Essa Análise É Importante

Um dashboard de vendas mostra que o faturamento caiu 8% no mês. Mas não responde: essa queda veio de clientes novos que não ficaram, ou de clientes antigos que estão saindo? A análise de coorte (safra) responde isso.

**Safra** é o mês em que o cliente fez seu primeiro faturamento. Ao agrupar clientes pela safra de entrada, conseguimos acompanhar o comportamento de cada "turma" ao longo do tempo — como uma foto do ciclo de vida do cliente.

### EXPLICAÇÃO PARA LEIGOS

Imagine uma escola que recebe turmas novas todo mês. A análise de safra é como acompanhar cada turma separadamente: quantos alunos da turma de janeiro ainda estão na escola em junho? E a turma de março? Se a turma de março perdeu alunos mais rápido, algo mudou — e vale investigar o quê.

---

## KPIs e Medidas Principais

| KPI | O que mede | Por que importa |
|-----|-----------|-----------------|
| **Clientes por coorte** | Quantos clientes entraram em cada mês | Mostra a capacidade de aquisição ao longo do tempo |
| **Retenção M1 / M2 / M3** | % de clientes ainda ativos após 1, 2 e 3 meses | Os primeiros 3 meses são críticos — se o cliente sobrevive até M3, a chance de ficar é muito maior |
| **Receita total por coorte** | Faturamento acumulado de cada safra | Nem toda safra vale igual — safras com ticket alto compensam menor volume |
| **Taxa de churn por canal** | % de perda por canal de venda | PME tipicamente tem churn mais rápido que Corporativo e Grandes Contas |
| **Reativações** | Clientes Lost que voltaram a faturar | Indica efetividade de ações de recuperação |

---

## Processo de ETL
```
SQL Server                    Power Query (Excel)              Python (Pandas)
    │                               │                               │
    ▼                               ▼                               ▼
 Query extrai 5 anos         Padroniza colunas,            Classifica status mês a mês,
 de faturamento com          trata tipos e datas,          constrói matriz de coorte,
 window functions            valida consistência           calcula retenção e gera outputs
 (primeira/última compra)
```

### 1. Extração (SQL)

A query em `sql/` extrai o histórico de faturamento dos últimos 5 anos, usando window functions para identificar a data do primeiro e último faturamento de cada cliente. Isso permite classificar a safra de entrada sem depender de tabela auxiliar.

### 2. Transformação (Python)

O script aplica as regras de negócio centralizadas em `src/utils/`:

- **Ativo**: faturamento em produto recorrente no mês
- **Lost**: 3+ meses consecutivos sem produto recorrente
- **Inativo**: 12+ meses sem nenhum faturamento
- **Reativado**: era Lost e voltou a faturar produto recorrente

A classificação é feita **mês a mês** para cada cliente, contando gaps consecutivos em produtos recorrentes.

### 3. Carga (Outputs)

Três artefatos padronizados na pasta `outputs/`.

---

## Como o Script Funciona (Passo a Passo)

O script `scripts/analise_safra.py` executa na seguinte ordem:

| Passo | O que faz | Por quê |
|-------|----------|---------|
| **1. Carregar dados** | Lê a base de vendas via `load_sales_data()` | Validação automática de colunas, tipos e valores ausentes |
| **2. Classificar status** | Aplica `classify_customer_status()` mês a mês | Identifica Ativo/Lost/Inativo/Reativado para cada cliente em cada mês |
| **3. Identificar safra** | Agrupa clientes pelo mês da primeira compra | Define a coorte de entrada de cada cliente |
| **4. Construir matriz de coorte** | Calcula retenção a cada mês de vida (M0, M1, M2...) | M0 = 100% por definição; a partir de M1 começa a curva de sobrevivência |
| **5. Segmentar por canal** | Repete a coorte para cada canal de venda | Churn em PME é diferente de Grandes Contas — tratar igual esconde o problema |
| **6. Analisar reativações** | Conta clientes Lost que voltaram, e após quantos meses | Mede a efetividade de ações de recuperação |
| **7. Gerar visualizações** | Heatmap de retenção + gráficos de evolução | Comunicação visual para apresentações executivas |
| **8. Validação (sanity checks)** | Confirma consistência dos números | Soma dos status = total de clientes; retenção entre 0% e 100% |
| **9. Exportar** | TXT + XLSX + PNG na pasta `outputs/` | Entrega padronizada para stakeholders |

---

## Query SQL Documentada

A query em `sql/` utiliza:

- **CTE com `ROW_NUMBER()`** para identificar o primeiro faturamento de cada cliente (define a safra)
- **CTE com `DATEDIFF()`** para calcular meses de vida desde a entrada
- **`LEFT JOIN`** com tabela de meses para garantir que meses sem faturamento apareçam como zero (não como NULL)
- **Filtros**: apenas faturamentos efetivados, valor > 0, últimos 5 anos

> **Nota:** Neste portfólio, a extração é simulada com dados sintéticos. A query está pronta para execução direta em SQL Server (SSMS ou DBeaver).

---

## Exemplos de Output

### Heatmap de Retenção por Coorte

![Heatmap Retenção](outputs/03_grafico_principal.png)

**Como ler este gráfico:** Cada linha é uma safra (mês de entrada). Cada coluna é o mês de vida (M0 = entrada, M1 = 1 mês depois...). A cor indica a % de retenção — verde escuro = alta retenção, vermelho = alta perda. Procure por:
- **Linhas que ficam vermelhas rápido** → safras com churn acelerado (investigar o que aconteceu naquele mês)
- **Colunas que escurecem da esquerda para a direita** → padrão natural de perda gradual
- **Platô** → quando a cor estabiliza, indica a base "hard core" que tende a ficar

### Tabela de Resultados (XLSX)

| Aba | Conteúdo | Uso |
|-----|----------|-----|
| **resumo** | KPIs por coorte: clientes, retenção M1/M2/M3, receita | Comparação rápida entre safras para priorização |
| **detalhe** | Matriz completa coorte × mês de vida com % de retenção | Investigação granular — qual mês exato a retenção cai |
| **parametros** | Regras aplicadas, janela temporal, data de geração | Rastreabilidade — saber exatamente como os números foram gerados |

### Resumo Executivo (TXT)

O arquivo `01_resumo_executivo.txt` contém:
- Resultado geral (safra com maior e menor retenção)
- Alertas (safras com queda acelerada)
- Ações recomendadas (foco de CRM, lifecycle)
- Próximos passos

---

## Insights Esperados

Com dados reais, um analista sênior buscaria os seguintes padrões:

1. **Safras mais antigas estabilizam** — após 12-18 meses, a retenção forma um platô. Esses são os clientes "hard core" que dificilmente saem. O tamanho desse platô indica a saúde real da carteira.

2. **PME tem churn mais rápido que Corporativo** — empresas menores trocam de fornecedor com mais facilidade. Isso não é necessariamente um problema se o custo de aquisição for proporcional.

3. **Reativações acontecem entre 4-8 meses** — clientes que voltam geralmente o fazem nessa janela. Após 8 meses sem contato, a probabilidade de retorno cai drasticamente.

4. **Safras de janeiro tendem a reter melhor** — hipótese: reajuste anual no início do ano fideliza por inércia contratual.

5. **Se a retenção das safras recentes está piorando** — sinal de alerta para a área comercial: algo mudou no produto, no onboarding ou na concorrência.

---

## Validações Realizadas

O script executa sanity checks automáticos antes de exportar:

| Validação | Critério | Por que importa |
|-----------|----------|-----------------|
| Soma de status | Ativo + Lost + Inativo = total de clientes da safra | Garante que nenhum cliente foi duplicado ou perdido na classificação |
| Retenção M0 | = 100% para toda safra | Por definição, no mês de entrada todos estão ativos |
| Retenção máxima | ≤ 100% em qualquer mês | Valor > 100% indicaria erro de contagem |
| Consistência de receita | Receita total > 0 para toda safra ativa | Safra sem receita mas com clientes indica problema nos dados |

---

## Limitações e Próximos Passos

**O que esta análise NÃO cobre:**
- Não identifica o **motivo** do churn (preço, atendimento, concorrência) — isso exigiria dados qualitativos
- Não diferencia churn voluntário de involuntário (empresa fechou vs. trocou de fornecedor)
- A retenção é binária (ativo/não ativo) — não captura redução gradual de ticket

**Evolução possível:**
- Incluir **análise de sobrevivência** (Kaplan-Meier) para estimar tempo médio até churn com intervalo de confiança
- Segmentar por **produto principal** (clientes que só têm VA vs. quem tem VA + VR + VC)
- Cruzar com **NPS ou pesquisa de satisfação** para correlacionar retenção com experiência
- Adicionar **teste de significância** para confirmar se a diferença entre canais é estatisticamente relevante

---

## Execução
```bash
# A partir da raiz do projeto
python 01_analise_safra/scripts/analise_safra.py
```

Para setup completo e geração de dados, consulte o [README na raiz do projeto](../README.md).
