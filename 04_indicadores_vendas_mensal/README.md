# 04 — Indicadores de Vendas Mensal (Real vs Meta)

## Pergunta de Negócio

> "Atingimos a meta do mês? Se não, onde exatamente ficou abaixo? Foi porque perdemos clientes (volume), porque o ticket caiu (preço), ou porque o mix de produtos mudou? Qual canal puxou o resultado para baixo?"

Essa é a pergunta que abre toda reunião de resultado. E a maioria das empresas responde com "ficamos 5% abaixo da meta" — sem dizer **onde** nem **por quê**. Esta análise responde as duas coisas.

---

## Por Que Essa Análise É Importante

Um dashboard mostra que o faturamento ficou R$ 200K abaixo do forecast. O diretor pergunta: "por quê?" Silêncio na sala. Alguém diz "vou levantar os dados". Três dias depois, chega um Excel com 15 abas que ninguém entende.

A análise de Real vs Forecast com decomposição de causa raiz resolve isso em minutos: não só mostra o gap, mas **decompõe** de onde veio — por canal, por regional, por produto — e explica se a perda foi por **volume** (menos clientes comprando), **preço** (ticket menor) ou **mix** (mudança na composição de produtos).

### EXPLICAÇÃO PARA LEIGOS

Imagine que você esperava ganhar R$ 10.000 no mês, mas recebeu R$ 9.200. A diferença é R$ 800. Mas de onde veio essa diferença?

- Você perdeu 2 clientes que pagavam R$ 300/mês = **efeito volume** (-R$ 600)
- Os clientes que ficaram pagaram um pouco menos que o combinado = **efeito preço** (-R$ 150)
- A interação entre as duas coisas = **efeito cruzado** (-R$ 50)
- Total: -R$ 600 + (-R$ 150) + (-R$ 50) = **-R$ 800** ✓

Agora você sabe: o problema principal é perda de clientes (75% do gap), não queda de preço. A ação é diferente: investir em retenção, não em reajuste de preço.

---

## KPIs e Medidas Principais

| KPI | O que mede | Por que importa |
|-----|-----------|-----------------|
| **Realizado mensal (R$)** | Faturamento efetivo do mês | O número real — ponto de partida |
| **Meta / Forecast (R$)** | Quanto era esperado faturar | A referência — sem meta, não há gap |
| **Gap absoluto (R$)** | Realizado − Meta | Tamanho do desvio em reais |
| **Gap percentual (%)** | Gap / Meta | Permite comparar meses com metas diferentes |
| **Efeito Volume** | (Δ clientes) × ticket anterior | Quanto do gap veio de ganho/perda de clientes |
| **Efeito Preço** | clientes anterior × (Δ ticket) | Quanto do gap veio de variação no ticket médio |
| **Efeito Cruzado** | (Δ clientes) × (Δ ticket) | Interação entre volume e preço simultâneos |

### Classificação de Status

| Status | Critério | Significado |
|--------|----------|-------------|
| 🟢 **Acima** | Gap > +2% | Superou a meta com margem |
| 🟡 **Na Meta** | Gap entre -2% e +2% | Dentro da faixa de tolerância |
| 🔴 **Abaixo** | Gap < -2% | Ficou abaixo — requer investigação |

---

## Decomposição de Causa Raiz

Esta é a parte mais valiosa da análise. A decomposição separa o gap total em **3 componentes aditivos**:
```
Gap Total = Efeito Volume + Efeito Preço + Efeito Cruzado
```

### Como Funciona (com números)

Suponha que no mês anterior tínhamos 100 clientes com ticket médio de R$ 1.000.
Neste mês temos 95 clientes com ticket médio de R$ 980.
```
Efeito Volume  = (95 − 100) × R$ 1.000 = −R$ 5.000
→ "Perdemos 5 clientes. Se o ticket tivesse ficado igual, perderíamos R$ 5K."

Efeito Preço   = 100 × (R$ 980 − R$ 1.000) = −R$ 2.000
→ "Os clientes que ficaram estão pagando R$ 20 a menos. Impacto: R$ 2K."

Efeito Cruzado = (95 − 100) × (R$ 980 − R$ 1.000) = +R$ 100
→ "Interação: os clientes que saíram já pagavam menos. Efeito residual."

Gap Total = −R$ 5.000 + (−R$ 2.000) + R$ 100 = −R$ 6.900 ✓
```

### O Que Cada Efeito Significa para o Negócio

| Efeito dominante | Diagnóstico | Ação recomendada |
|-----------------|-------------|------------------|
| **Volume** | Perda (ou ganho) de clientes ativos | Retenção, aquisição, win-back |
| **Preço** | Clientes estão pagando mais/menos | Revisar pricing, renegociações, downgrades |
| **Cruzado** | Ambos acontecendo ao mesmo tempo | Investigar se é um padrão ou coincidência |

---

## Processo de ETL
```
SQL Server                    Power Query (Excel)              Python (Pandas)
    │                               │                               │
    ▼                               ▼                               ▼
 Query extrai realizado       Padroniza colunas,            Compara real vs forecast,
 e forecast por canal ×       valida chaves e tipos,        decompõe causa raiz,
 produto × mês               trata missing values          gera narrativa + outputs
```

### 1. Extração (SQL)

A query em `sql/` extrai duas bases:
- **Realizado**: faturamento efetivo agregado por canal × produto × mês
- **Forecast**: meta definida pela área comercial na mesma granularidade

O JOIN entre as duas é feito por chave composta (canal + produto + mês).

### 2. Transformação (Python)

O script calcula:
- Gap absoluto e percentual por combinação canal × produto × mês
- Status (Acima / Na Meta / Abaixo) com tolerância de ±2%
- Decomposição em efeitos Volume, Preço e Cruzado por canal
- Narrativa executiva automática em texto

### 3. Carga (Outputs)

Três artefatos padronizados + narrativa na pasta `outputs/`.

---

## Como o Script Funciona (Passo a Passo)

| Passo | O que faz | Por quê |
|-------|----------|---------|
| **1. Carregar dados** | Lê base de vendas + tabela de forecast | Duas fontes distintas que precisam ser integradas |
| **2. Validar** | Confere se forecast tem valores positivos e chaves batem | Meta zerada ou ausente invalida toda a análise |
| **3. Consolidar mensal** | Agrega realizado por mês e compara com forecast total | Visão macro: "atingimos ou não?" |
| **4. Detalhar por dimensão** | Repete a comparação por canal, regional e produto | Visão drill-down: "onde exatamente ficou abaixo?" |
| **5. Decompor causa raiz** | Calcula efeitos Volume, Preço e Cruzado por canal | Responde "por quê ficou abaixo?" — não só "onde" |
| **6. Gerar narrativa** | Texto automático com diagnóstico e ações | O analista não precisa escrever — o script gera a conclusão |
| **7. Gerar visualizações** | Linhas Real vs Meta + waterfall + heatmap | Comunicação visual para reunião de resultado |
| **8. Validação** | Volume + Preço + Cruzado ≈ Gap Total (tolerância R$ 0.01) | Prova matemática de que a decomposição está correta |
| **9. Exportar** | TXT + XLSX + PNG na pasta `outputs/` | Entrega padronizada |

---

## Query SQL Documentada

A query em `sql/` retorna dois conjuntos de dados:

**Base de realizado:**
- Faturamento mensal por canal × produto com contagem de clientes ativos e ticket médio
- Filtros: apenas faturamento efetivado, valor > 0

**Base de forecast:**
- Meta mensal por canal × produto (definida pela área comercial)
- Granularidade deve bater com a do realizado para o JOIN funcionar

> **Nota:** Neste portfólio, o forecast é gerado sinteticamente por `generate_sample_data.py`. A query está pronta para execução direta em SQL Server.

---

## Exemplos de Output

### Gráfico Principal — Real vs Meta ao Longo do Tempo

![Real vs Meta](outputs/03_grafico_principal.png)

**Como ler este gráfico:**
- **Linha azul** = realizado (o que efetivamente faturamos)
- **Linha tracejada cinza** = meta / forecast (o que era esperado)
- **Área verde** = meses em que superamos a meta
- **Área vermelha** = meses em que ficamos abaixo
- **Distância entre as linhas** = tamanho do gap — quanto maior, mais urgente a investigação

**O que procurar:**
- Se a linha azul está consistentemente abaixo da cinza → problema estrutural (não pontual)
- Se há um mês específico com queda abrupta → evento pontual (investigar o que aconteceu)
- Se as linhas estão convergindo → tendência de melhora (ações recentes podem estar funcionando)

### Tabela de Resultados (XLSX)

| Aba | Conteúdo | Uso |
|-----|----------|-----|
| **resumo** | Real, meta, gap (R$ e %) por mês + status (Acima/Na Meta/Abaixo) | Priorização mensal: quais meses precisam de investigação? |
| **detalhe** | Drill-down por canal × produto × mês com efeitos Volume/Preço/Cruzado | Investigação: exatamente qual canal e produto puxou o gap |
| **parametros** | Tolerância (±2%), método de decomposição, data de geração | Rastreabilidade completa |

---

## Insights Esperados

Com dados reais, um analista sênior buscaria:

1. **Gap dominado por Efeito Volume** → o problema é **retenção ou aquisição**. Estamos perdendo clientes ou não estamos conquistando novos na velocidade esperada. Ação: alinhar com a equipe comercial sobre pipeline e churn.

2. **Gap dominado por Efeito Preço** → os clientes estão, mas gastam menos. Possíveis causas: downgrades, renegociações, concorrência pressionando preço. Ação: revisar política de pricing e verificar se há padrão de downgrade por canal.

3. **Canal específico puxa o resultado para baixo** → o gap total pode estar mascarando que 3 canais bateram meta e 1 puxou tudo para baixo. O waterfall revela exatamente a contribuição de cada canal.

4. **Meses de janeiro consistentemente acima da meta** → efeito reajuste anual. Se a meta não incorpora sazonalidade, vai parecer que janeiro é "ótimo" e dezembro é "péssimo" quando na verdade é o padrão esperado.

5. **Efeito Cruzado relevante** → volume e preço estão mudando ao mesmo tempo na mesma direção. Pode indicar uma mudança estrutural no perfil da carteira (ex: clientes grandes saindo e pequenos entrando).

---

## Validações Realizadas

| Validação | Critério | Por que importa |
|-----------|----------|-----------------|
| Meta positiva | Forecast > 0 para todos os períodos | Meta zerada ou negativa invalida o cálculo de gap % |
| Chave de join | Canal × produto × mês bate entre real e forecast | Dimensões desalinhadas geram gaps fantasmas |
| Decomposição | Volume + Preço + Cruzado ≈ Gap Total (±R$ 0.01) | Prova matemática: se não bate, tem erro no cálculo |
| Status | Soma dos gaps por canal = gap total | Nenhuma dimensão foi perdida ou duplicada na decomposição |
| Completude | Todos os meses do período têm dado de real e forecast | Mês ausente distorce a série temporal |

---

## Limitações e Próximos Passos

**O que esta análise NÃO cobre:**
- Não questiona se a **meta em si** é realista — se a meta foi definida sem base histórica, o gap pode refletir má definição, não má execução
- A decomposição é **aditiva e determinística** — não captura efeitos não lineares ou variáveis ocultas
- Não inclui **margem/rentabilidade** — bater meta em receita com margem negativa não é bom resultado

**Evolução possível:**
- **Forecast dinâmico**: substituir meta fixa por modelo preditivo (média móvel, ARIMA, Prophet) que se ajusta com dados recentes
- **Decomposição por mix de produto**: separar quanto do gap veio de mudança na composição (ex: mais produto barato, menos caro)
- **Drill-down até gerência/vendedor**: localizar o gap no nível mais granular para ação direta
- **Intervalo de confiança**: em vez de meta pontual, usar faixa esperada para reduzir falsos alertas
- **Integração com Power BI**: transformar a narrativa automática em tooltip dinâmico no dashboard

---

## Execução
```bash
# A partir da raiz do projeto
python 04_indicadores_vendas_mensal/scripts/analise_indicadores.py
```

Para setup completo e geração de dados, consulte o [README na raiz do projeto](../README.md).
