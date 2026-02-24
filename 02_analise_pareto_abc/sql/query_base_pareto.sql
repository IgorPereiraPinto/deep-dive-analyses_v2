/*
═══════════════════════════════════════════════════════════════════
QUERY: Base para Análise de Pareto / Curva ABC
═══════════════════════════════════════════════════════════════════

OBJETIVO:
    Agregar o faturamento total por cliente para classificação ABC.
    Cada linha do resultado representa UM cliente com suas métricas
    consolidadas, pronto para o ranking de Pareto no Python.

PERGUNTA DE NEGÓCIO:
    "Quais 20% dos clientes representam 80% da receita?
     Qual o nível de dependência de poucos clientes?"

COMO ESTA QUERY SE CONECTA AO PYTHON:
    1. Você executa esta query no SQL Server (SSMS ou DBeaver)
    2. Exporta o resultado como CSV ou conecta via pyodbc
    3. O script analise_pareto.py lê o CSV, classifica ABC e gera outputs

    No portfólio, esse passo é simulado com dados sintéticos.
    A query está pronta para execução direta em SQL Server.

COLUNAS RETORNADAS:
    - cliente_id          → identificador único do cliente
    - receita             → faturamento total no período (R$) — coluna obrigatória no Python
    - ticket_medio        → receita / número de transações
    - meses_ativo         → em quantos meses distintos o cliente faturou
    - qtd_transacoes      → total de transações no período
    - qtd_produtos        → quantos produtos distintos contratou
    - canal               → canal de venda (PME, Corporativo, etc.)
    - regiao              → região geográfica
    - primeira_compra     → data da primeira transação
    - ultima_compra       → data da última transação
    - meses_relacionamento → tempo entre primeira e última compra

    O script Python espera no mínimo: cliente_id, receita.
    As demais colunas permitem segmentações adicionais.

BANCO DE DADOS ESPERADO:
    - dbo.faturamento  → tabela de fatos (uma linha por transação)
    - dbo.clientes     → dimensão de clientes (canal, região, gerência)
    - dbo.produtos     → dimensão de produtos (nome, tipo)

PRÉ-REQUISITOS:
    - SQL Server 2016+ (usa window functions e STRING_AGG)
    - Acesso de leitura às tabelas acima

AUTOR: Igor Pereira Pinto
═══════════════════════════════════════════════════════════════════
*/


-- ═══════════════════════════════════════════════════════════════
-- CTE 1: MÉTRICAS BASE POR CLIENTE
-- ═══════════════════════════════════════════════════════════════
-- Agrega TODAS as transações de cada cliente em uma única linha.
-- Isso é necessário porque a classificação ABC trabalha com um
-- valor por cliente (receita total), não com transações individuais.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   Se o cliente 123 fez 50 compras ao longo de 3 anos, esta CTE
--   consolida tudo em: "cliente 123 faturou R$ 500K no total,
--   com ticket médio de R$ 10K, ativo em 30 meses, com 3 produtos".

WITH metricas_cliente AS (
    SELECT
        f.cliente_id,

        -- Métricas de receita
        SUM(f.valor_faturamento)                    AS receita,
        AVG(f.valor_faturamento)                    AS ticket_medio,

        -- Métricas de atividade
        COUNT(*)                                     AS qtd_transacoes,
        COUNT(DISTINCT FORMAT(f.data_faturamento, 'yyyy-MM'))
                                                     AS meses_ativo,
        COUNT(DISTINCT f.produto_id)                 AS qtd_produtos,

        -- Datas de referência
        MIN(f.data_faturamento)                      AS primeira_compra,
        MAX(f.data_faturamento)                      AS ultima_compra,
        DATEDIFF(
            MONTH,
            MIN(f.data_faturamento),
            MAX(f.data_faturamento)
        )                                            AS meses_relacionamento

    FROM
        dbo.faturamento f
    WHERE
        f.valor_faturamento > 0                      -- Apenas faturamento positivo
        AND f.status_faturamento = 'Efetivado'       -- Sem cancelamentos/estornos
        AND f.data_faturamento >= DATEADD(YEAR, -5, GETDATE())  -- Últimos 5 anos
    GROUP BY
        f.cliente_id
),


-- ═══════════════════════════════════════════════════════════════
-- CTE 2: RANKING E % ACUMULADO
-- ═══════════════════════════════════════════════════════════════
-- Ordena clientes do maior para o menor faturamento e calcula
-- o percentual acumulado. É a base da Curva de Pareto.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   Colocamos todos os clientes em fila do mais valioso ao menos.
--   Depois vamos somando: "o 1º representa 5%, o 1º+2º = 9%,
--   o 1º+2º+3º = 12%..." até chegar em 100%.
--   Quando a soma passa de 80%, todos até ali são Classe A.
--
-- POR QUE CALCULAR NO SQL E NÃO SÓ NO PYTHON?
--   Em bases muito grandes (milhões de transações), é mais eficiente
--   fazer a agregação no banco e trazer só o resultado consolidado.
--   O Python recebe ~5K linhas (clientes) em vez de ~500K (transações).

ranking_pareto AS (
    SELECT
        mc.*,

        -- Posição no ranking (1 = maior receita)
        ROW_NUMBER() OVER (ORDER BY mc.receita DESC) AS posicao_ranking,

        -- % da receita individual
        mc.receita * 1.0 / SUM(mc.receita) OVER ()   AS pct_receita,

        -- % acumulado (base para classificação ABC)
        SUM(mc.receita) OVER (
            ORDER BY mc.receita DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) * 1.0 / SUM(mc.receita) OVER ()            AS pct_acumulado

    FROM
        metricas_cliente mc
)


-- ═══════════════════════════════════════════════════════════════
-- QUERY PRINCIPAL: CLIENTES COM CLASSIFICAÇÃO ABC
-- ═══════════════════════════════════════════════════════════════
-- Junta as métricas do cliente com a classificação ABC e as
-- dimensões (canal, região) para segmentação no Python.
--
-- A classificação é feita direto no SQL usando CASE:
--   pct_acumulado ≤ 0.80 → Classe A
--   pct_acumulado ≤ 0.95 → Classe B
--   restante             → Classe C
--
-- EXPLICAÇÃO PARA LEIGOS:
--   O resultado final é uma lista de todos os clientes, ordenada
--   do mais valioso ao menos, com a informação de quanto cada um
--   representa na receita total e em qual classe (A, B ou C) se
--   enquadra. É como um "ranking de importância" da carteira.

SELECT
    rp.posicao_ranking,
    rp.cliente_id,
    c.canal_venda                                       AS canal,
    c.regiao,
    c.gerencia,

    -- Métricas de receita
    rp.receita,
    rp.ticket_medio,
    rp.pct_receita,
    rp.pct_acumulado,

    -- Classificação ABC
    CASE
        WHEN rp.pct_acumulado <= 0.80 THEN 'A'
        WHEN rp.pct_acumulado <= 0.95 THEN 'B'
        ELSE 'C'
    END                                                 AS classe_abc,

    -- Métricas de atividade (contexto para decisão)
    rp.meses_ativo,
    rp.qtd_transacoes,
    rp.qtd_produtos,
    rp.meses_relacionamento,
    rp.primeira_compra,
    rp.ultima_compra,

    -- Flag de risco: cliente A que está há 3+ meses sem comprar
    CASE
        WHEN rp.pct_acumulado <= 0.80
             AND DATEDIFF(MONTH, rp.ultima_compra, GETDATE()) >= 3
        THEN 'SIM'
        ELSE 'NAO'
    END                                                 AS alerta_cliente_a_inativo

FROM
    ranking_pareto      rp
    INNER JOIN dbo.clientes c ON rp.cliente_id = c.cliente_id

ORDER BY
    rp.receita DESC;


/*
═══════════════════════════════════════════════════════════════════
ÍNDICES RECOMENDADOS (para performance)
═══════════════════════════════════════════════════════════════════

-- Índice principal na tabela de faturamento:
CREATE NONCLUSTERED INDEX IX_faturamento_cliente_receita
ON dbo.faturamento (cliente_id, data_faturamento)
INCLUDE (valor_faturamento, status_faturamento, produto_id);

-- Na tabela de clientes:
CREATE NONCLUSTERED INDEX IX_clientes_id_canal
ON dbo.clientes (cliente_id)
INCLUDE (canal_venda, regiao, gerencia);


═══════════════════════════════════════════════════════════════════
COMO EXPORTAR O RESULTADO PARA O PYTHON
═══════════════════════════════════════════════════════════════════

OPÇÃO 1 — CSV via SSMS:
    Execute a query → botão direito no resultado → "Save Results As..."
    Salve como CSV na pasta data/ do projeto.

OPÇÃO 2 — Conexão direta via pyodbc:
    import pyodbc
    import pandas as pd

    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=seu_servidor;"
        "DATABASE=seu_banco;"
        "Trusted_Connection=yes;"
    )

    df = pd.read_sql(open("sql/query_base_pareto.sql").read(), conn)
    df.to_csv("data/base_vendas_historica.csv", index=False)

OPÇÃO 3 — Power Query (Excel):
    Dados → Obter Dados → Do SQL Server → cole a query no editor avançado


═══════════════════════════════════════════════════════════════════
QUERIES DE VALIDAÇÃO (rode no SSMS para conferir)
═══════════════════════════════════════════════════════════════════

-- 1. Verificar total de clientes e receita
SELECT
    COUNT(DISTINCT cliente_id) AS total_clientes,
    SUM(valor_faturamento)     AS receita_total
FROM dbo.faturamento
WHERE valor_faturamento > 0
  AND data_faturamento >= DATEADD(YEAR, -5, GETDATE());

-- 2. Distribuição por classe ABC (conferir se A ≈ 80%)
WITH abc AS (
    SELECT
        cliente_id,
        SUM(valor_faturamento) AS receita,
        SUM(SUM(valor_faturamento)) OVER (
            ORDER BY SUM(valor_faturamento) DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) * 1.0 / SUM(SUM(valor_faturamento)) OVER () AS pct_acum
    FROM dbo.faturamento
    WHERE valor_faturamento > 0
      AND data_faturamento >= DATEADD(YEAR, -5, GETDATE())
    GROUP BY cliente_id
)
SELECT
    CASE
        WHEN pct_acum <= 0.80 THEN 'A'
        WHEN pct_acum <= 0.95 THEN 'B'
        ELSE 'C'
    END AS classe,
    COUNT(*)         AS clientes,
    SUM(receita)     AS receita_classe
FROM abc
GROUP BY
    CASE
        WHEN pct_acum <= 0.80 THEN 'A'
        WHEN pct_acum <= 0.95 THEN 'B'
        ELSE 'C'
    END
ORDER BY classe;

-- 3. Top 10 clientes (conferir concentração)
SELECT TOP 10
    cliente_id,
    SUM(valor_faturamento) AS receita
FROM dbo.faturamento
WHERE valor_faturamento > 0
  AND data_faturamento >= DATEADD(YEAR, -5, GETDATE())
GROUP BY cliente_id
ORDER BY receita DESC;

-- 4. Clientes A que não compram há 3+ meses (alerta)
SELECT COUNT(*) AS clientes_a_inativos
FROM (
    SELECT cliente_id, MAX(data_faturamento) AS ultima
    FROM dbo.faturamento
    WHERE valor_faturamento > 0
    GROUP BY cliente_id
    HAVING SUM(valor_faturamento) > 0
) sub
WHERE DATEDIFF(MONTH, sub.ultima, GETDATE()) >= 3;

═══════════════════════════════════════════════════════════════════
*/
