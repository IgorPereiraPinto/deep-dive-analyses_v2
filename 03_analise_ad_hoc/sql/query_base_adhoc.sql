/*
═══════════════════════════════════════════════════════════════════
QUERY: Base para Análise Ad Hoc (Exploratória Sob Demanda)
═══════════════════════════════════════════════════════════════════

OBJETIVO:
    Extrair dados para duas investigações rápidas:
    (a) Queda de receita por produto — comparação entre janelas temporais
    (b) Correlação entre desconto concedido e ticket médio por cliente

PERGUNTAS DE NEGÓCIO:
    "Quais produtos tiveram a maior queda nos últimos meses?"
    "Estamos dando desconto demais? Isso gera volume ou destrói valor?"

COMO ESTA QUERY SE CONECTA AO PYTHON:
    1. Execute esta query no SQL Server (SSMS ou DBeaver)
    2. Exporte como CSV ou conecte via pyodbc
    3. O script analise_adhoc.py lê o CSV e executa as duas investigações

    No portfólio, esse passo é simulado com dados sintéticos.
    A query está pronta para execução direta em SQL Server.

COLUNAS RETORNADAS:
    - cliente_id      → identificador único do cliente
    - data            → data da transação (obrigatória no Python)
    - produto         → nome do produto (obrigatória no Python)
    - receita         → valor faturado (obrigatória no Python)
    - desconto_pct    → percentual de desconto concedido (obrigatória no Python)
    - canal           → canal de venda (para segmentações futuras)
    - regiao          → região geográfica (para segmentações futuras)
    - tipo_produto    → recorrente ou complementar

    O script Python espera no mínimo:
    Investigação (a): data, produto, receita
    Investigação (b): cliente_id, receita, desconto_pct

BANCO DE DADOS ESPERADO:
    - dbo.faturamento  → tabela de fatos (uma linha por transação)
    - dbo.clientes     → dimensão de clientes
    - dbo.produtos     → dimensão de produtos
    - dbo.descontos    → tabela de descontos aplicados (ou campo na faturamento)

PRÉ-REQUISITOS:
    - SQL Server 2016+
    - Acesso de leitura às tabelas acima

AUTOR: Igor Pereira Pinto
═══════════════════════════════════════════════════════════════════
*/


-- ═══════════════════════════════════════════════════════════════
-- CTE 1: FATURAMENTO COM DESCONTO POR TRANSAÇÃO
-- ═══════════════════════════════════════════════════════════════
-- Junta o faturamento com a informação de desconto aplicado.
-- Cada linha é UMA transação com o desconto que foi concedido.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   O vendedor pode dar desconto na hora da venda. Precisamos
--   registrar quanto de desconto cada transação recebeu para
--   depois analisar se dar desconto ajuda ou atrapalha.
--
-- POR QUE CALCULAR O DESCONTO COMO PERCENTUAL?
--   Um desconto de R$ 50 num produto de R$ 500 (10%) é diferente
--   de R$ 50 num produto de R$ 5.000 (1%). O percentual torna
--   a comparação justa entre produtos de tickets diferentes.

WITH faturamento_desconto AS (
    SELECT
        f.cliente_id,
        f.data_faturamento                              AS data,
        p.nome_produto                                  AS produto,
        f.valor_faturamento                             AS receita,

        -- Desconto como percentual (0 a 1)
        -- Se a tabela não tem campo de desconto, usar a diferença
        -- entre preço de tabela e preço praticado:
        CASE
            WHEN f.valor_tabela > 0
            THEN (f.valor_tabela - f.valor_faturamento) * 1.0 / f.valor_tabela
            ELSE 0
        END                                             AS desconto_pct,

        -- Dimensões para segmentação (opcionais no Python)
        c.canal_venda                                   AS canal,
        c.regiao,
        c.gerencia,
        CASE
            WHEN p.nome_produto IN ('Vale Alimentação', 'Vale Refeição', 'Vale Combustível')
            THEN 'recorrente'
            ELSE 'complementar'
        END                                             AS tipo_produto

    FROM
        dbo.faturamento         f
        INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
        INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id
    WHERE
        f.valor_faturamento > 0                          -- Sem estornos
        AND f.status_faturamento = 'Efetivado'           -- Apenas confirmados
        AND f.data_faturamento >= DATEADD(YEAR, -2, GETDATE())  -- Últimos 2 anos
                                                         -- (suficiente para janelas de 5 meses)
)


-- ═══════════════════════════════════════════════════════════════
-- QUERY PRINCIPAL: DADOS PARA AS DUAS INVESTIGAÇÕES
-- ═══════════════════════════════════════════════════════════════
--
-- O Python recebe esta tabela e executa duas análises diferentes:
--
-- INVESTIGAÇÃO (a) — Queda de receita por produto:
--   Usa as colunas: data, produto, receita
--   Agrega receita por produto × mês, compara janelas temporais
--   e identifica quais produtos caíram.
--
-- INVESTIGAÇÃO (b) — Correlação desconto × ticket:
--   Usa as colunas: cliente_id, receita, desconto_pct
--   Agrupa por cliente, calcula médias e mede correlação de Pearson.
--
-- POR QUE UMA ÚNICA QUERY PARA DUAS INVESTIGAÇÕES?
--   Eficiência. A base é a mesma — faturamento com desconto.
--   Fazer duas queries separadas leria a mesma tabela duas vezes.
--   O Python filtra e agrega conforme cada investigação precisa.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   É como pedir uma única cópia do extrato bancário e usar
--   a mesma folha para duas análises diferentes: uma olhando
--   por produto (qual vendeu menos?) e outra por cliente
--   (quem recebeu desconto gastou mais ou menos?).

SELECT
    fd.cliente_id,
    fd.data,
    fd.produto,
    fd.receita,
    fd.desconto_pct,
    fd.canal,
    fd.regiao,
    fd.gerencia,
    fd.tipo_produto,

    -- Campos auxiliares para facilitar agregação no Python
    FORMAT(fd.data, 'yyyy-MM')                          AS mes_ref,
    DATEPART(QUARTER, fd.data)                          AS trimestre,
    DATEPART(YEAR, fd.data)                             AS ano

FROM
    faturamento_desconto fd

ORDER BY
    fd.data,
    fd.produto,
    fd.cliente_id;


/*
═══════════════════════════════════════════════════════════════════
NOTA SOBRE O CAMPO DE DESCONTO
═══════════════════════════════════════════════════════════════════

Nem toda empresa tem um campo "desconto" explícito na tabela de
faturamento. Alternativas comuns:

CENÁRIO 1 — Campo direto:
    A tabela faturamento tem coluna "desconto_pct" ou "desconto_valor".
    → Usar diretamente.

CENÁRIO 2 — Preço de tabela vs preço praticado:
    A tabela tem "valor_tabela" (preço cheio) e "valor_faturamento"
    (preço praticado). O desconto é a diferença:
    → desconto_pct = (valor_tabela - valor_faturamento) / valor_tabela
    → É o que usamos nesta query.

CENÁRIO 3 — Tabela separada de condições comerciais:
    Existe uma tabela dbo.condicoes_comerciais com regras por cliente.
    → Fazer JOIN adicional e trazer o desconto contratual.

CENÁRIO 4 — Sem informação de desconto:
    Se não há dado de desconto disponível:
    → A Investigação (b) não pode ser executada.
    → O script Python trata isso graciosamente (pula a análise).
    → A Investigação (a) funciona normalmente sem desconto.

Adapte a CTE faturamento_desconto conforme o cenário da sua empresa.


═══════════════════════════════════════════════════════════════════
VARIAÇÃO: QUERY ESPECÍFICA PARA INVESTIGAÇÃO (A)
═══════════════════════════════════════════════════════════════════

Se você só precisa da análise de queda (sem desconto), esta query
simplificada é mais rápida:

SELECT
    FORMAT(f.data_faturamento, 'yyyy-MM')   AS mes_ref,
    p.nome_produto                          AS produto,
    SUM(f.valor_faturamento)                AS receita,
    COUNT(DISTINCT f.cliente_id)            AS clientes_ativos,
    COUNT(*)                                AS transacoes
FROM
    dbo.faturamento         f
    INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id
WHERE
    f.valor_faturamento > 0
    AND f.status_faturamento = 'Efetivado'
    AND f.data_faturamento >= DATEADD(MONTH, -6, GETDATE())
GROUP BY
    FORMAT(f.data_faturamento, 'yyyy-MM'),
    p.nome_produto
ORDER BY
    mes_ref, produto;


═══════════════════════════════════════════════════════════════════
VARIAÇÃO: QUERY ESPECÍFICA PARA INVESTIGAÇÃO (B)
═══════════════════════════════════════════════════════════════════

Se você só precisa da análise de correlação desconto × ticket:

SELECT
    f.cliente_id,
    AVG(f.valor_faturamento)                            AS ticket_medio,
    AVG(
        CASE
            WHEN f.valor_tabela > 0
            THEN (f.valor_tabela - f.valor_faturamento) * 1.0 / f.valor_tabela
            ELSE 0
        END
    )                                                   AS desconto_medio,
    COUNT(*)                                            AS transacoes,
    c.canal_venda                                       AS canal
FROM
    dbo.faturamento         f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
WHERE
    f.valor_faturamento > 0
    AND f.status_faturamento = 'Efetivado'
    AND f.data_faturamento >= DATEADD(YEAR, -1, GETDATE())
GROUP BY
    f.cliente_id,
    c.canal_venda
HAVING
    COUNT(*) >= 3   -- Mínimo de 3 transações para média confiável
ORDER BY
    ticket_medio DESC;


═══════════════════════════════════════════════════════════════════
QUERIES DE VALIDAÇÃO (rode no SSMS para conferir)
═══════════════════════════════════════════════════════════════════

-- 1. Verificar se há dados nos últimos 6 meses (suficiente para janelas)
SELECT
    FORMAT(data_faturamento, 'yyyy-MM') AS mes,
    COUNT(*)                            AS registros,
    SUM(valor_faturamento)              AS receita
FROM dbo.faturamento
WHERE data_faturamento >= DATEADD(MONTH, -6, GETDATE())
  AND valor_faturamento > 0
GROUP BY FORMAT(data_faturamento, 'yyyy-MM')
ORDER BY mes;

-- 2. Verificar cobertura de desconto (quantos registros têm desconto?)
SELECT
    CASE WHEN valor_tabela > 0 THEN 'COM desconto calculável'
         ELSE 'SEM desconto' END           AS status_desconto,
    COUNT(*)                                AS registros,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS pct
FROM dbo.faturamento
WHERE data_faturamento >= DATEADD(YEAR, -1, GETDATE())
GROUP BY
    CASE WHEN valor_tabela > 0 THEN 'COM desconto calculável'
         ELSE 'SEM desconto' END;

-- 3. Distribuição de desconto (verificar se valores fazem sentido)
SELECT
    CASE
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0    THEN '0% (sem desconto)'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.05 THEN '1-5%'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.10 THEN '5-10%'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.20 THEN '10-20%'
        ELSE '20%+'
    END                                     AS faixa_desconto,
    COUNT(*)                                AS registros
FROM dbo.faturamento
WHERE valor_faturamento > 0
  AND valor_tabela > 0
  AND data_faturamento >= DATEADD(YEAR, -1, GETDATE())
GROUP BY
    CASE
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0    THEN '0% (sem desconto)'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.05 THEN '1-5%'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.10 THEN '5-10%'
        WHEN (valor_tabela - valor_faturamento) * 1.0 / NULLIF(valor_tabela, 0) <= 0.20 THEN '10-20%'
        ELSE '20%+'
    END
ORDER BY faixa_desconto;

-- 4. Top 5 produtos por receita (conferir se estão na base)
SELECT TOP 5
    p.nome_produto,
    SUM(f.valor_faturamento) AS receita
FROM dbo.faturamento f
INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id
WHERE f.valor_faturamento > 0
  AND f.data_faturamento >= DATEADD(MONTH, -6, GETDATE())
GROUP BY p.nome_produto
ORDER BY receita DESC;

═══════════════════════════════════════════════════════════════════
*/
