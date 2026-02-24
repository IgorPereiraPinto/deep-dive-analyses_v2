# Outputs — Indicadores de Vendas Mensal (Real vs Meta)

Esta pasta contém os artefatos gerados pela execução de `scripts/analise_indicadores.py`.

| Arquivo | Formato | Para quem | Conteúdo |
|---------|---------|-----------|----------|
| `01_resumo_executivo.txt` | Texto | Diretoria / gestores | Diagnóstico completo: resultado do mês, drivers de gap, decomposição de causa raiz (volume/preço) e ações — leitura em 3 minutos |
| `02_tabela_resultados.xlsx` | Excel | Analistas / planejamento | 3 abas: **resumo** (real vs meta por mês + status), **detalhe** (drill-down por canal × regional × produto), **parametros** (tolerância, método, rastreabilidade) |
| `03_grafico_principal.png` | Imagem | Apresentações executivas | Linhas Real vs Meta com gaps visuais (verde = acima, vermelho = abaixo) |
| `resumo_real_vs_forecast.csv` | CSV | Visualização no GitHub | Tabela de resumo mensal renderizada nativamente pelo GitHub |

## Como Regenerar
```bash
# A partir da raiz do projeto
python generate_sample_data.py                                        # gera dados sintéticos (se ainda não gerou)
python 04_indicadores_vendas_mensal/scripts/analise_indicadores.py    # executa a análise e salva aqui
```

## Como Ler o Gráfico (Real vs Meta)

![Real vs Meta](03_grafico_principal.png)

- **Linha azul com pontos** = realizado (o que efetivamente faturamos)
- **Linha tracejada cinza** = meta / forecast (o que era esperado)
- **Linhas verticais verdes** = meses em que superamos a meta
- **Linhas verticais vermelhas** = meses em que ficamos abaixo
- **Comprimento da linha vertical** = tamanho do gap em R$

**O que procurar:**

| Padrão visual | Significado | Ação |
|--------------|------------|------|
| Linha azul consistentemente abaixo da cinza | Problema estrutural (meta irrealista ou performance crônica) | Revisar meta OU plano de ação abrangente |
| Uma queda abrupta em mês específico | Evento pontual (perda de cliente grande, sazonalidade, problema operacional) | Investigar o que aconteceu naquele mês |
| Linhas convergindo (azul subindo em direção à cinza) | Tendência de recuperação — ações recentes podem estar funcionando | Manter e acelerar as ações em curso |
| Gap aumentando progressivamente | Deterioração — o problema está piorando mês a mês | Ação urgente: reunião de guerra com comercial |

## Como Ler o Excel

Abra `02_tabela_resultados.xlsx`:

| Aba | O que contém | Como usar |
|-----|-------------|-----------|
| **resumo** | Real, meta, gap (R$ e %), status (🟢 Acima / 🟡 Na Meta / 🔴 Abaixo) por mês | Visão rápida: quais meses atingiram e quais não? Há tendência? |
| **detalhe** | Drill-down: cada combinação canal × regional × produto × mês com gap individual | Localizar exatamente onde está o problema: "Canal PME, Regional Sudeste, Vale Combustível em dezembro" |
| **parametros** | Tolerância (±2%), método de decomposição, fonte do forecast, data de geração | Rastreabilidade: qualquer pessoa reproduz a análise com os mesmos critérios |

### Como Usar a Aba Detalhe para Investigação

1. **Filtre por status = "Abaixo"** → ver apenas as combinações problemáticas
2. **Ordene por gap (R$) crescente** → o maior gap negativo é o primeiro a investigar
3. **Filtre por canal** → ver se o problema é concentrado num canal ou generalizado
4. **Compare meses** → o gap é recorrente ou pontual?

## Como Ler o Resumo Executivo (TXT)

O arquivo `01_resumo_executivo.txt` tem 5 blocos:

| Bloco | O que contém | Para quê |
|-------|-------------|----------|
| **Resultado do último mês** | Real, meta, gap e status com emoji | Resposta em 10 segundos: "atingimos ou não?" |
| **Visão do período** | Quantos meses acima, na meta e abaixo | Tendência: estamos melhorando ou piorando? |
| **Drivers de gap** | Produto e canal que mais puxaram para baixo e para cima | Priorização: o que atacar primeiro? |
| **Decomposição de causa raiz** | Efeitos Volume, Preço e Cruzado com % do gap | Diagnóstico: perdemos clientes ou o ticket caiu? |
| **Ações recomendadas** | Ações numeradas com justificativa | Próximos passos concretos |

### Entendendo a Decomposição de Causa Raiz

| Efeito | Significado | Se for o dominante → Ação |
|--------|------------|--------------------------|
| **Volume** | Mudança na quantidade de clientes ativos | Pipeline de aquisição + estratégia de retenção |
| **Preço** | Mudança no ticket médio dos clientes existentes | Revisar pricing, renegociações, downgrades |
| **Cruzado** | Volume e preço mudaram ao mesmo tempo | Investigar se é mudança estrutural no perfil da carteira |

A soma dos 3 efeitos é **sempre** igual ao gap total — isso é uma propriedade matemática, não coincidência. Se não bater, tem erro no cálculo.

## Relação com as Outras Análises do Portfólio

| Análise | Como complementa esta |
|---------|----------------------|
| **01 — Safra (Coorte)** | Se o efeito volume é dominante, a análise de safra mostra QUANDO e QUAIS coortes estão saindo |
| **02 — Pareto (ABC)** | Se poucos clientes puxaram o gap, o Pareto mostra se são Classe A (risco crítico) ou C (baixo impacto) |
| **03 — Ad Hoc** | Se um produto específico lidera a queda, a análise ad hoc investiga se há relação com desconto |

> **Nota:** Os arquivos nesta pasta são gerados com dados sintéticos determinísticos (`seed=42`). Em ambiente real, seriam atualizados mensalmente após o fechamento do período.
