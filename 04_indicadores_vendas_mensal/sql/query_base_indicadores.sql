/*
═══════════════════════════════════════════════════════════════════
QUERY: Base para Análise de Indicadores (Real vs Meta / Forecast)
═══════════════════════════════════════════════════════════════════

OBJETIVO:
    Extrair duas bases que o Python precisa para comparar realizado
    com a meta e decompor causa raiz:
    (1) Faturamento realizado por canal × regional × produto × mês
    (2) Forecast / meta na mesma granularidade

PERGUNTAS DE NEGÓCIO:
    "Atingimos a meta do mês?"
    "Onde exatamente ficou abaixo — qual canal, regional, produto?"
    "Foi por perda de clientes (volume) ou queda de ticket (preço)?"

COMO ESTA QUERY SE CONECTA AO PYTHON:
    1. Execute as duas queries abaixo no SQL Server
    2. Exporte cada resultado como CSV:
       - base_vendas_historica.csv  (Query 1)
       - forecast_mensal.csv        (Query 2)
    3. O script analise_indicadores.py lê os dois CSVs,
       compara, decompõe causa raiz e gera outputs

    No portfólio, ambas as bases são simuladas com dados sintéticos.
    As queries estão prontas para execução direta em SQL Server.

COLUNAS RETORNADAS:
    Query 1 (Realizado):
    - cliente_id   → identificador do cliente (para decomposição volume/preço)
    - data         → data da transação
    - receita      → valor faturado (R$)
    - canal        → canal de venda
    - regional     → regional / região
    - produto      → nome do produto

    Query 2 (Forecast):
    - mes_ref       → período no formato YYYY-MM
    - canal         → canal de venda (mesma chave do realizado)
    - regional      → regional (mesma chave do realizado)
    - produto       → produto (mesma chave do realizado)
    - meta_receita  → valor esperado (R$)

    IMPORTANTE: As chaves de join (canal, regional, produto) devem
    usar os MESMOS nomes e valores nas duas bases. Se "PME" no
    realizado está como "Pequenas Empresas" no forecast, o join falha.

BANCO DE DADOS ESPERADO:
    - dbo.faturamento     → tabela de fatos (transações)
    - dbo.clientes        → dimensão de clientes
    - dbo.produtos        → dimensão de produtos
    - dbo.forecast_mensal → tabela de metas por dimensão e mês

PRÉ-REQUISITOS:
    - SQL Server 2016+
    - Acesso de leitura às tabelas acima

AUTOR: Igor Pereira Pinto
═══════════════════════════════════════════════════════════════════
*/


-- ═══════════════════════════════════════════════════════════════
-- QUERY 1: FATURAMENTO REALIZADO (base_vendas_historica.csv)
-- ═══════════════════════════════════════════════════════════════
-- Extrai o histórico de vendas no nível transacional.
-- O Python agrega conforme a necessidade de cada etapa:
--   - Visão macro: agrupa por mes_ref
--   - Drill-down: agrupa por mes_ref × canal × regional × produto
--   - Decomposição: agrupa por mes_ref × canal (com cliente_id para
--     contar clientes únicos e calcular ticket médio)
--
-- POR QUE TRAZER NO NÍVEL TRANSACIONAL E NÃO JÁ AGREGADO?
--   Porque a decomposição de causa raiz precisa do cliente_id
--   para contar clientes únicos (efeito volume) e calcular
--   ticket médio (efeito preço). Se agregássemos aqui, perderíamos
--   essa informação.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   Esta query traz cada venda individual dos últimos 2 anos.
--   O Python depois agrupa de diferentes formas: por mês (visão
--   geral), por canal (onde está o gap), por cliente (causa raiz).

SELECT
    f.cliente_id,
    f.data_faturamento                                  AS data,
    f.valor_faturamento                                 AS receita,
    c.canal_venda                                       AS canal,
    c.regiao                                            AS regional,
    p.nome_produto                                      AS produto

FROM
    dbo.faturamento         f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
    INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id

WHERE
    f.valor_faturamento > 0                              -- Sem estornos
    AND f.status_faturamento = 'Efetivado'               -- Apenas confirmados
    AND f.data_faturamento >= DATEADD(YEAR, -2, GETDATE())  -- Últimos 2 anos

ORDER BY
    f.data_faturamento,
    c.canal_venda,
    f.cliente_id;


-- ═══════════════════════════════════════════════════════════════
-- QUERY 2: FORECAST / META MENSAL (forecast_mensal.csv)
-- ═══════════════════════════════════════════════════════════════
-- Extrai a meta definida pela área comercial, na mesma
-- granularidade que o realizado: canal × regional × produto × mês.
--
-- EXPLICAÇÃO PARA LEIGOS:
--   Todo mês, a diretoria comercial define quanto espera faturar.
--   Essa meta é quebrada por canal, regional e produto. Esta query
--   traz exatamente essa tabela para o Python comparar com o
--   faturamento real.
--
-- POR QUE A GRANULARIDADE PRECISA SER A MESMA?
--   Se a meta está no nível "canal × produto" e o realizado no
--   nível "canal × regional × produto", o join não funciona.
--   As chaves DEVEM ter a mesma granularidade nas duas bases.
--   Se a meta na sua empresa é menos granular (ex: só por canal),
--   adapte a query abaixo ou distribua proporcionalmente.
--
-- CENÁRIOS COMUNS DE GRANULARIDADE DE META:
--   (a) Meta por canal × produto × mês         → ideal, é o que usamos
--   (b) Meta só por canal × mês                → distribuir por produto proporcionalmente
--   (c) Meta total da empresa por mês           → distribuir por canal e produto
--   (d) Meta por vendedor × mês                 → agregar por canal/regional

SELECT
    FORMAT(fm.mes_referencia, 'yyyy-MM')                AS mes_ref,
    fm.canal_venda                                      AS canal,
    fm.regiao                                           AS regional,
    fm.nome_produto                                     AS produto,
    fm.valor_meta                                       AS meta_receita

FROM
    dbo.forecast_mensal fm

WHERE
    fm.valor_meta > 0                                    -- Meta deve ser positiva
    AND fm.mes_referencia >= DATEADD(YEAR, -2, GETDATE())  -- Mesmo período do realizado

ORDER BY
    fm.mes_referencia,
    fm.canal_venda,
    fm.nome_produto;


/*
═══════════════════════════════════════════════════════════════════
NOTA SOBRE A TABELA DE FORECAST
═══════════════════════════════════════════════════════════════════

Nem toda empresa tem uma tabela de forecast estruturada no banco.
Cenários comuns e como adaptar:

CENÁRIO 1 — Tabela dedicada (dbo.forecast_mensal):
    Ideal. Use a Query 2 diretamente.

CENÁRIO 2 — Meta numa planilha Excel:
    A área comercial manda a meta por e-mail todo mês numa planilha.
    → Importe o Excel para o SQL Server via SSIS ou bcp
    → Ou leia diretamente no Python com pd.read_excel()

CENÁRIO 3 — Meta calculada como % de crescimento sobre histórico:
    Não existe tabela de meta explícita. A meta é "crescer 5% sobre
    o mesmo mês do ano anterior".
    → Calcule no SQL:

    SELECT
        FORMAT(DATEADD(YEAR, 1, f.data_faturamento), 'yyyy-MM') AS mes_ref,
        c.canal_venda    AS canal,
        c.regiao         AS regional,
        p.nome_produto   AS produto,
        SUM(f.valor_faturamento) * 1.05  AS meta_receita  -- +5%
    FROM dbo.faturamento f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
    INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id
    WHERE f.valor_faturamento > 0
      AND f.data_faturamento >= DATEADD(YEAR, -3, GETDATE())
      AND f.data_faturamento <  DATEADD(YEAR, -1, GETDATE())
    GROUP BY
        FORMAT(DATEADD(YEAR, 1, f.data_faturamento), 'yyyy-MM'),
        c.canal_venda, c.regiao, p.nome_produto;

CENÁRIO 4 — Meta definida no CRM (Salesforce, HubSpot):
    → Extrair via API ou relatório do CRM
    → Padronizar nomes de canal/produto para bater com o faturamento


═══════════════════════════════════════════════════════════════════
VARIAÇÃO: QUERY JÁ AGREGADA (se não precisa de decomposição)
═══════════════════════════════════════════════════════════════════

Se você só precisa da comparação Real vs Meta (sem decomposição
de causa raiz em volume/preço), pode trazer já agregado:

SELECT
    FORMAT(f.data_faturamento, 'yyyy-MM')   AS mes_ref,
    c.canal_venda                           AS canal,
    c.regiao                                AS regional,
    p.nome_produto                          AS produto,
    SUM(f.valor_faturamento)                AS realizado,
    COUNT(DISTINCT f.cliente_id)            AS clientes_ativos,
    AVG(f.valor_faturamento)                AS ticket_medio

FROM
    dbo.faturamento         f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
    INNER JOIN dbo.produtos p ON f.produto_id = p.produto_id
WHERE
    f.valor_faturamento > 0
    AND f.status_faturamento = 'Efetivado'
    AND f.data_faturamento >= DATEADD(YEAR, -2, GETDATE())
GROUP BY
    FORMAT(f.data_faturamento, 'yyyy-MM'),
    c.canal_venda,
    c.regiao,
    p.nome_produto
ORDER BY
    mes_ref, canal, produto;

-- Depois faça JOIN com a Query 2 (forecast) no Python ou no SQL.


═══════════════════════════════════════════════════════════════════
VARIAÇÃO: QUERY COM DECOMPOSIÇÃO JÁ NO SQL
═══════════════════════════════════════════════════════════════════

Se preferir calcular a decomposição de causa raiz direto no SQL
(sem depender do Python), use CTEs encadeadas:

WITH mes_atual AS (
    SELECT
        c.canal_venda                       AS canal,
        COUNT(DISTINCT f.cliente_id)        AS clientes,
        SUM(f.valor_faturamento)            AS receita,
        AVG(f.valor_faturamento)            AS ticket_medio
    FROM dbo.faturamento f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
    WHERE f.data_faturamento >= DATEADD(MONTH, -1, CAST(GETDATE() AS DATE))
      AND f.valor_faturamento > 0
    GROUP BY c.canal_venda
),

mes_anterior AS (
    SELECT
        c.canal_venda                       AS canal,
        COUNT(DISTINCT f.cliente_id)        AS clientes,
        SUM(f.valor_faturamento)            AS receita,
        AVG(f.valor_faturamento)            AS ticket_medio
    FROM dbo.faturamento f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
    WHERE f.data_faturamento >= DATEADD(MONTH, -2, CAST(GETDATE() AS DATE))
      AND f.data_faturamento <  DATEADD(MONTH, -1, CAST(GETDATE() AS DATE))
      AND f.valor_faturamento > 0
    GROUP BY c.canal_venda
)

SELECT
    COALESCE(a.canal, b.canal)              AS canal,
    ISNULL(a.clientes, 0)                   AS clientes_atual,
    ISNULL(b.clientes, 0)                   AS clientes_ant,
    ISNULL(a.ticket_medio, 0)               AS ticket_atual,
    ISNULL(b.ticket_medio, 0)               AS ticket_ant,

    -- Efeito Volume: (Δ clientes) × ticket anterior
    (ISNULL(a.clientes, 0) - ISNULL(b.clientes, 0))
        * ISNULL(b.ticket_medio, 0)         AS efeito_volume,

    -- Efeito Preço: clientes anterior × (Δ ticket)
    ISNULL(b.clientes, 0)
        * (ISNULL(a.ticket_medio, 0) - ISNULL(b.ticket_medio, 0))
                                            AS efeito_preco,

    -- Efeito Cruzado: (Δ clientes) × (Δ ticket)
    (ISNULL(a.clientes, 0) - ISNULL(b.clientes, 0))
        * (ISNULL(a.ticket_medio, 0) - ISNULL(b.ticket_medio, 0))
                                            AS efeito_cruzado,

    -- Gap total (para validação: volume + preço + cruzado = gap)
    ISNULL(a.receita, 0) - ISNULL(b.receita, 0) AS gap_total

FROM
    mes_atual   a
    FULL OUTER JOIN mes_anterior b ON a.canal = b.canal

ORDER BY
    gap_total;


═══════════════════════════════════════════════════════════════════
QUERIES DE VALIDAÇÃO (rode no SSMS para conferir)
═══════════════════════════════════════════════════════════════════

-- 1. Verificar se realizado e forecast cobrem os mesmos meses
SELECT 'realizado' AS fonte, FORMAT(data_faturamento, 'yyyy-MM') AS mes,
       COUNT(*) AS registros
FROM dbo.faturamento
WHERE data_faturamento >= DATEADD(YEAR, -2, GETDATE())
  AND valor_faturamento > 0
GROUP BY FORMAT(data_faturamento, 'yyyy-MM')

UNION ALL

SELECT 'forecast', FORMAT(mes_referencia, 'yyyy-MM'),
       COUNT(*)
FROM dbo.forecast_mensal
WHERE mes_referencia >= DATEADD(YEAR, -2, GETDATE())
  AND valor_meta > 0
GROUP BY FORMAT(mes_referencia, 'yyyy-MM')
ORDER BY mes, fonte;


-- 2. Verificar aderência de chaves (canais que existem numa
--    base mas não na outra → join vai falhar)
SELECT 'canal_so_no_realizado' AS tipo, c.canal_venda AS valor
FROM dbo.faturamento f
INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
WHERE c.canal_venda NOT IN (
    SELECT DISTINCT canal_venda FROM dbo.forecast_mensal
)
GROUP BY c.canal_venda

UNION ALL

SELECT 'canal_so_no_forecast', canal_venda
FROM dbo.forecast_mensal
WHERE canal_venda NOT IN (
    SELECT DISTINCT c.canal_venda
    FROM dbo.faturamento f
    INNER JOIN dbo.clientes c ON f.cliente_id = c.cliente_id
)
GROUP BY canal_venda;


-- 3. Resumo de meta por canal (conferir se valores fazem sentido)
SELECT
    canal_venda                     AS canal,
    COUNT(DISTINCT FORMAT(mes_referencia, 'yyyy-MM')) AS meses,
    SUM(valor_meta)                 AS meta_total,
    AVG(valor_meta)                 AS meta_media_mensal
FROM dbo.forecast_mensal
WHERE valor_meta > 0
  AND mes_referencia >= DATEADD(YEAR, -1, GETDATE())
GROUP BY canal_venda
ORDER BY meta_total DESC;


-- 4. Validar decomposição: soma dos efeitos = gap total
--    (rode após a query de decomposição acima)
SELECT
    SUM(efeito_volume + efeito_preco + efeito_cruzado) AS soma_efeitos,
    SUM(gap_total)                                      AS gap_real,
    SUM(efeito_volume + efeito_preco + efeito_cruzado)
        - SUM(gap_total)                                AS diferenca
FROM (
    -- cole aqui o resultado da query de decomposição
    SELECT * FROM #decomposicao_temp
) d;

═══════════════════════════════════════════════════════════════════
*/
