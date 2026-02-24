# 03 — Análise Ad Hoc (Exploratória Sob Demanda)

## Pergunta de Negócio

> "Quais produtos tiveram a maior queda de receita nos últimos meses? Existe relação entre o nível de desconto concedido e o ticket médio do cliente?"

São perguntas que surgem numa reunião de resultado, num e-mail do diretor comercial numa sexta às 17h, ou numa hipótese levantada pelo time de pricing. Não cabem num dashboard fixo — precisam de investigação rápida e pontual.

---

## Por Que Essa Análise É Importante

Dashboards respondem "o quê" aconteceu. Mas quando o gestor pergunta "por que o produto X caiu 15%?" ou "será que estamos dando desconto demais?", o dashboard fica mudo. É aí que entra a análise ad hoc.

Ad hoc significa "para isto" — é uma análise feita sob demanda para responder uma pergunta específica. O valor não está na ferramenta, está na velocidade e na clareza da resposta.

### EXPLICAÇÃO PARA LEIGOS

Imagine que o gerente comercial chega na sua mesa e pergunta: "estou sentindo que o produto Vale Combustível caiu muito nos últimos meses — é verdade ou impressão?" 

A análise ad hoc é a resposta estruturada: "Sim, caiu 12.3% comparando os últimos 2 meses com os 3 anteriores. E não é só impressão — é o 3º maior delta negativo entre todos os produtos. Além disso, os clientes que recebem mais desconto nesse produto têm ticket médio menor, o que sugere que o desconto não está gerando volume adicional."

Isso é o que diferencia um analista sênior de alguém que só faz relatório.

---

## KPIs e Medidas Principais

| KPI | O que mede | Por que importa |
|-----|-----------|-----------------|
| **Delta de receita por produto** | Diferença absoluta (R$) entre os 2 meses recentes e os 3 anteriores | Identifica quais produtos estão perdendo fôlego — e o tamanho do impacto |
| **Delta percentual (%)** | Variação relativa entre as duas janelas | Produto pequeno pode ter queda absoluta baixa mas % enorme — ambos importam |
| **Correlação desconto × ticket médio** | Coeficiente de correlação linear (Pearson) | Se a correlação é negativa, clientes com mais desconto gastam menos — o desconto pode estar destruindo valor |

### Como Ler a Correlação

| Valor | Interpretação |
|-------|--------------|
| **+0.7 a +1.0** | Correlação forte positiva — mais desconto, maior ticket (desconto gera volume) |
| **+0.3 a +0.7** | Correlação moderada positiva |
| **-0.3 a +0.3** | Correlação fraca — desconto não tem efeito claro no ticket |
| **-0.7 a -0.3** | Correlação moderada negativa — desconto pode estar atraindo perfil de baixo ticket |
| **-1.0 a -0.7** | Correlação forte negativa — desconto está destruindo valor |

---

## Processo de ETL
```
SQL Server                    Power Query (Excel)              Python (Pandas)
    │                               │                               │
    ▼                               ▼                               ▼
 Query extrai receita         Padroniza colunas,            Compara janelas temporais,
 mensal por produto com       valida tipos e datas,         calcula deltas e correlação,
 campos de desconto           trata missing values          gera diagnóstico + outputs
```

### 1. Extração (SQL)

A query em `sql/` extrai o faturamento mensal agregado por produto, com campos de desconto médio e ticket médio por cliente. Inclui filtros para eliminar estornos e transações não efetivadas.

### 2. Transformação (Python)

O script executa duas investigações independentes:

**Investigação 1 — Queda de Receita por Produto:**
- Agrega receita por produto × mês
- Define duas janelas: os **2 meses mais recentes** vs. os **3 meses anteriores**
- Calcula delta absoluto (R$) e delta percentual (%)
- Rankeia por maior queda

**Investigação 2 — Relação Desconto × Ticket Médio:**
- Calcula ticket médio e desconto médio por cliente
- Estima correlação linear (Pearson) entre as duas variáveis
- Gera scatter plot para visualizar a relação

### 3. Carga (Outputs)

Três artefatos padronizados na pasta `outputs/`.

---

## Como o Script Funciona (Passo a Passo)

| Passo | O que faz | Por quê |
|-------|----------|---------|
| **1. Carregar dados** | Lê a base de vendas e valida schema | Garantir que colunas de receita, produto e data existem |
| **2. Consolidar por produto × mês** | Agrega receita mensal por produto | Base para comparação entre janelas temporais |
| **3. Definir janelas temporais** | 2 meses recentes vs 3 anteriores | Compara "agora" com "antes" para detectar tendência |
| **4. Calcular deltas** | Receita recente − receita anterior (absoluto e %) | Identifica quais produtos estão caindo e o tamanho da queda |
| **5. Rankear quedas** | Ordena por maior delta negativo | Prioriza investigação: o que caiu mais merece atenção primeiro |
| **6. Calcular correlação** | Pearson entre desconto médio e ticket médio por cliente | Testa a hipótese: "dar desconto gera mais receita?" |
| **7. Gerar visualizações** | Barras de delta por produto + scatter desconto × ticket | Comunicação visual direta |
| **8. Validação** | Confere janelas temporais e integridade dos dados | Garante que a comparação é justa (mesmos critérios) |
| **9. Exportar** | TXT + XLSX + PNG na pasta `outputs/` | Entrega padronizada |

---

## Query SQL Documentada

A query em `sql/` retorna:

- **Receita mensal por produto**: base para a comparação entre janelas
- **Desconto médio por cliente**: para a análise de correlação
- **Ticket médio por cliente**: para cruzar com desconto
- **Quantidade de transações**: contexto (volume vs. valor)

> **Nota:** Neste portfólio, a extração é simulada com dados sintéticos. A query está pronta para execução direta em SQL Server.

---

## Exemplos de Output

### Gráfico Principal — Delta de Receita por Produto

![Delta Receita](outputs/03_grafico_principal.png)

**Como ler este gráfico:**
- **Barras para a esquerda (negativas)** = produtos que perderam receita → necessitam intervenção prioritária
- **Barras para a direita (positivas)** = produtos que cresceram
- **Quanto maior a barra**, maior o impacto absoluto em R$
- Ordene mentalmente: o produto com a maior barra negativa é o primeiro a investigar

### Scatter — Correlação Desconto × Ticket Médio

O gráfico complementar mostra cada cliente como um ponto:
- **Eixo X** = desconto médio concedido (%)
- **Eixo Y** = ticket médio (R$)
- Se os pontos formam uma **nuvem descendente** (mais desconto → menor ticket): o desconto pode estar destruindo valor
- Se formam uma **nuvem ascendente** ou sem padrão: o desconto não tem efeito claro

### Tabela de Resultados (XLSX)

| Aba | Conteúdo | Uso |
|-----|----------|-----|
| **resumo** | Top produtos com maior queda (delta R$ e %) + coeficiente de correlação | Resposta direta às duas perguntas de negócio |
| **detalhe** | Série mensal completa por produto + dados por cliente para correlação | Investigação granular — ver mês a mês quando a queda começou |
| **parametros** | Janelas temporais usadas, método de correlação, data de geração | Rastreabilidade — reproduzir a análise com os mesmos critérios |

---

## Insights Esperados

Com dados reais, um analista sênior buscaria:

1. **Produto com queda absoluta grande mas % pequena** → produto maduro perdendo volume gradualmente. Pode ser natural (mercado encolhendo) ou sinal de concorrência.

2. **Produto com queda % grande mas absoluto pequeno** → produto pequeno em crise. Isoladamente não impacta o resultado total, mas pode ser indicador antecipado de problema maior.

3. **Correlação negativa entre desconto e ticket** → o desconto está atraindo clientes de perfil inferior, não aumentando o volume dos existentes. Recomendação: revisar política de desconto — talvez substituir por benefícios (prazo, serviço) em vez de preço.

4. **Correlação próxima de zero** → desconto não tem efeito mensurável no comportamento de compra. O dinheiro gasto em desconto pode estar sendo desperdiçado.

5. **Queda concentrada nos 2 últimos meses** → evento recente (mudança de preço, saída de representante, problema operacional). Diferente de uma tendência lenta de 6+ meses.

---

## Validações Realizadas

| Validação | Critério | Por que importa |
|-----------|----------|-----------------|
| Janelas temporais | Ambas com dados suficientes (sem meses zerados) | Comparação justa — se uma janela tem mês faltando, o delta é enganoso |
| Correlação | Coeficiente entre -1 e +1 | Valor fora dessa faixa indica erro no cálculo |
| Produtos | Todos os produtos aparecem em ambas as janelas | Produto novo que só existe na janela recente distorce o delta |
| Receita | Soma dos deltas individuais ≈ delta total | Consistência entre a visão produto a produto e o total |

---

## Limitações e Próximos Passos

**O que esta análise NÃO cobre:**
- Não explica **por que** o produto caiu (preço, concorrência, sazonalidade, problema operacional) — aponta onde investigar
- A correlação desconto × ticket é **linear e bivariada** — pode haver variáveis confundidoras (canal, região, porte do cliente)
- As janelas temporais são fixas (2 vs 3 meses) — em cenários com alta sazonalidade, isso pode gerar falsos positivos

**Evolução possível:**
- **Decomposição do delta**: separar queda por volume (menos clientes comprando) vs. preço (ticket menor)
- **Regressão múltipla**: incluir canal, região e porte como variáveis de controle na análise de desconto
- **Teste de significância**: verificar se as quedas são estatisticamente relevantes ou variação normal
- **Análise de elasticidade**: medir quanto a demanda muda para cada 1% de desconto adicional
- **Automatizar alertas**: disparar investigação automática quando um produto cai mais que X% em relação à média

---

## Execução
```bash
# A partir da raiz do projeto
python 03_analise_ad_hoc/scripts/analise_adhoc.py
```

Para setup completo e geração de dados, consulte o [README na raiz do projeto](../README.md).
