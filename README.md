# Deep Dive Analyses — Análises Avançadas de Vendas

**Portfólio executável** que demonstra como um Analista de Dados/BI Sênior responde perguntas reais de negócio com análises aprofundadas em Python, partindo de dados extraídos via SQL Server.

> Dashboards mostram **o quê** aconteceu. Deep dives explicam **por quê** aconteceu e **o que fazer** a respeito.

O projeto usa dados sintéticos determinísticos (`seed=42`) que simulam 5 anos de faturamento de uma operadora de benefícios corporativos. A estrutura está pronta para integração direta com SQL Server em ambiente de produção.

**Stack:** Python (Pandas · NumPy · Matplotlib · Seaborn) · SQL Server (queries documentadas) · Excel (outputs formatados)

---

## Contexto de Negócio

A empresa simulada vende cartões de benefícios (Vale Alimentação, Refeição, Combustível) para empresas de diferentes portes. O faturamento é recorrente: a empresa-cliente paga mensalmente por funcionário ativo em cada produto contratado.

**Canais de venda:** Pequenas Empresas (PME) · Corporativo · Grandes Contas · Setor Público — cada um com dinâmicas de churn, ticket e ciclo de venda distintas.

**Desafios típicos do negócio:**
- Qual o tempo médio até um cliente se tornar inativo? Isso varia por canal?
- 20% dos clientes representam 80% da receita — essa concentração está aumentando?
- Atingimos a meta do mês? Se não, foi por perda de clientes ou queda de ticket?
- Quais produtos tiveram queda recente e existe correlação com nível de desconto?

Cada uma das 4 análises deste repositório responde uma dessas perguntas.

---

## As 4 Análises

| # | Análise | Pergunta de Negócio | Técnica |
|---|---------|---------------------|---------|
| 01 | [Análise de Safra (Coorte)](01_analise_safra/) | Dos clientes que entraram em Jan/2021, quantos ainda estão ativos? | Cohort analysis com classificação de ciclo de vida |
| 02 | [Pareto / Curva ABC](02_analise_pareto_abc/) | Quais clientes concentram a receita e qual o risco disso? | Classificação ABC com evolução temporal |
| 03 | [Análise Ad Hoc](03_analise_ad_hoc/) | Existe sazonalidade? Quais produtos cresceram ou caíram? | Toolkit exploratório sob demanda |
| 04 | [Real vs Forecast](04_indicadores_vendas_mensal/) | Atingimos a meta? Onde ficou abaixo e por quê? | Decomposição de causa raiz (volume × preço × mix) |

Cada análise possui seu próprio **README.md** com: pergunta de negócio, processo de ETL, metodologia, query SQL documentada, passo a passo do script, exemplos de output e insights.

---

## Estrutura do Repositório
```
deep-dive-analyses_v2/
├── README.md                              ← você está aqui
├── requirements.txt                       ← dependências do projeto
├── .gitignore
├── .env.example                           ← template de variáveis de ambiente
├── generate_sample_data.py                ← gerador de dados sintéticos (seed=42)
├── validate_outputs.py                    ← quality gate — valida outputs das análises
│
├── src/utils/                             ← módulos compartilhados
│   ├── __init__.py
│   └── excel.py                           ← export Excel com freeze_panes + abas padronizadas
│
├── data/                                  ← dados gerados para simulação
│
├── 01_analise_safra/                      ← Coorte e ciclo de vida do cliente
│   ├── README.md
│   ├── sql/
│   ├── scripts/
│   └── outputs/                           ← TXT + XLSX + PNG
│
├── 02_analise_pareto_abc/                 ← Concentração de receita (ABC)
│   ├── README.md
│   ├── sql/
│   ├── scripts/
│   └── outputs/
│
├── 03_analise_ad_hoc/                     ← Análises exploratórias sob demanda
│   ├── README.md
│   ├── sql/
│   ├── scripts/
│   └── outputs/
│
└── 04_indicadores_vendas_mensal/          ← Real vs Meta com causa raiz
    ├── README.md
    ├── sql/
    ├── scripts/
    └── outputs/
```

---

## Glossário de Termos de Negócio

| Termo | Definição |
|-------|-----------|
| **Ativo** | Cliente com faturamento em pelo menos um produto recorrente no mês |
| **Lost (Perdido)** | 3+ meses consecutivos sem faturamento em produto recorrente |
| **Inativo** | 12+ meses sem nenhum faturamento |
| **Reativado** | Cliente Lost que voltou a faturar produto recorrente |
| **Safra (Coorte)** | Mês do primeiro faturamento do cliente — define o grupo de entrada |
| **Classe ABC** | Classificação por contribuição de receita: A (0–80%), B (80–95%), C (95–100%) |
| **Forecast** | Meta de faturamento definida pela área comercial para o mês |
| **Efeito Volume** | Impacto em R$ causado por variação no número de clientes ativos |
| **Efeito Preço** | Impacto em R$ causado por variação no ticket médio |

---

## Setup
```bash
# Clonar o repositório
git clone https://github.com/IgorPereiraPinto/deep-dive-analyses_v2.git
cd deep-dive-analyses_v2

# Criar ambiente virtual e instalar dependências
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Execução (ordem obrigatória)
```bash
# 1. Gerar dados sintéticos (~60K–120K registros, 5 anos)
python generate_sample_data.py

# 2. Executar as 4 análises na ordem
python 01_analise_safra/scripts/analise_safra.py
python 02_analise_pareto_abc/scripts/analise_pareto.py
python 03_analise_ad_hoc/scripts/analise_adhoc.py
python 04_indicadores_vendas_mensal/scripts/analise_indicadores.py

# 3. Validar que todos os outputs foram gerados corretamente
python validate_outputs.py
```

---

## Como Interpretar os Outputs

Cada análise gera **3 artefatos obrigatórios** na pasta `<analise>/outputs/`:

| Artefato | Para quem | O que contém |
|----------|-----------|-------------|
| `01_resumo_executivo.txt` | Diretoria / gestores | Insights, riscos identificados, ações recomendadas e próximos passos — leitura em 2 minutos |
| `02_tabela_resultados.xlsx` | Analistas / planejamento | Aba **resumo** (KPIs para priorização), aba **detalhe** (granularidade para investigação), aba **parametros** (rastreabilidade: regras aplicadas, janelas temporais, data de geração) |
| `03_grafico_principal.png` | Apresentações executivas | Visualização principal da análise, pronta para inserir em slides ou relatórios |

---

## Fluxo Geral
```
SQL Server  →  Power Query (Excel)  →  Python (Pandas/NumPy)  →  Visualizações + Insights
     ↓                ↓                        ↓                         ↓
  Extração       Tratamento            Análise aprofundada        Entrega para decisão
```

Neste portfólio, o passo de SQL Server é simulado com dados sintéticos gerados por `generate_sample_data.py`. As queries SQL estão documentadas na pasta `sql/` de cada análise, prontas para execução em ambiente real.

---

## Checklist de Qualidade

- [x] Estrutura de pastas e arquivos conforme especificação
- [x] Dependências mínimas declaradas em `requirements.txt`
- [x] Dados sintéticos determinísticos (`seed=42` — resultados reprodutíveis)
- [x] Volume da base dentro de faixa moderada (60K–120K registros)
- [x] 4 análises implementadas com ETL documentado
- [x] Cada análise gera TXT + XLSX + PNG em `outputs/`
- [x] XLSX padronizado com abas `resumo`, `detalhe`, `parametros`
- [x] Quality gate `validate_outputs.py` com status PASS
- [x] Documentação executiva e técnica em PT-BR
- [x] Queries SQL documentadas para cada análise

---

## Observações Técnicas

- Dados são gerados em runtime via `generate_sample_data.py` — sem dependências externas
- Scripts usam backend `Agg` do Matplotlib para execução headless (servidores sem interface gráfica)
- Export Excel com freeze_panes no cabeçalho e truncamento automático de nome de aba (limite 31 chars)
- Caso ocorra erro de caminho ou import, aplicar correção mínima e reexecutar o pipeline

---

## Próximos Passos

1. **Integração com SQL Server** — conectar via pyodbc/sqlalchemy para leitura direta de fatos e dimensões
2. **Testes estatísticos** — incluir intervalos de confiança e testes de significância nas comparações
3. **Monitoramento contínuo** — automatizar execução mensal com alertas por e-mail via Power Automate
4. **Dashboard Power BI** — evoluir os outputs para dashboard interativo com refresh automatizado via Gateway

---

## Autor

**Igor Pereira Pinto** — Analista de Dados/BI e Planejamento Comercial Sênior

- [LinkedIn](https://www.linkedin.com/in/igorpereirapinto/)
- [Portfólio](https://sites.google.com/view/portfolio-de-projetos/home)
- [GitHub](https://github.com/IgorPereiraPinto)
