# Assistente Virtual de Dados

Um chatbot inteligente que responde perguntas em linguagem natural consultando um banco de dados SQLite, utilizando LangGraph para orquestração de agentes.

## Sumario

- [Instrucoes de Execucao](#instrucoes-de-execucao)
- [Arquitetura](#arquitetura)
- [Fluxo do Agente](#fluxo-do-agente)
- [Exemplos de Consultas](#exemplos-de-consultas)
- [Sugestoes de Melhorias](#sugestoes-de-melhorias)

---

## Instrucoes de Execucao

### Pre-requisitos

- Python 3.11 ou superior
- Chave de API do OpenAI ou Google Gemini

### Instalacao

1. Clone o repositorio:
```bash
git clone https://github.com/seu-usuario/assistente-virtual-dados.git
cd assistente-virtual-dados
```

2. Crie um ambiente virtual (recomendado):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Instale as dependencias:
```bash
pip install -r requirements.txt
```

4. Configure as variaveis de ambiente:
```bash
cp .env.example .env
```

Edite o arquivo `.env` e adicione sua chave de API:
```
LLM_PROVIDER=gemini
GOOGLE_API_KEY=sua_chave_aqui
```

Ou para usar OpenAI:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sua_chave_aqui
```

5. Execute a aplicacao:
```bash
python -m streamlit run app.py
```

A aplicacao estara disponivel em `http://localhost:8501`

---

## Arquitetura

### Visao Geral

O sistema e composto por tres camadas principais:

```
+------------------------------------------------------------------+
|                      STREAMLIT FRONTEND                           |
|  [Chat Input] [Raciocinio] [Tabela] [Graficos] [LLM Selector]    |
+--------------------------------+---------------------------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                     LANGGRAPH SQL AGENT                           |
|                                                                   |
|  +----------+   +----------+   +----------+   +----------+       |
|  | 1.List   |-->| 2.Schema |-->| 3.Query  |-->| 4.Execute|       |
|  |  Tables  |   |          |   |  Gen     |   |          |       |
|  +----------+   +----------+   +----------+   +----+-----+       |
|                                                    |              |
|                                        +-----------+----------+   |
|  +----------+                          | 5.Error Handler      |   |
|  |6.Response|<-------------------------+    (retry loop)      |   |
|  |  Format  |                          +----------------------+   |
|  +----------+                                                     |
+--------------------------------+---------------------------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                         SQLITE DATABASE                           |
|  [clientes] [compras] [suporte] [campanhas_marketing]            |
+------------------------------------------------------------------+
```

### Estrutura de Arquivos

```
assistente-virtual-dados/
|-- app.py                    # Aplicacao Streamlit
|-- requirements.txt          # Dependencias Python
|-- .env.example              # Template de variaveis de ambiente
|-- anexo_desafio_1.db        # Banco de dados SQLite
|
+-- src/
    |-- __init__.py
    |-- config.py             # Configuracoes centralizadas
    |
    +-- agent/
    |   |-- __init__.py
    |   |-- llm.py            # Factory para OpenAI e Gemini
    |   |-- prompts.py        # Prompts do sistema
    |   +-- sql_agent.py      # Agente SQL com LangGraph StateGraph
    |
    +-- database/
    |   |-- __init__.py
    |   +-- connection.py     # Conexao com SQLite
    |
    +-- visualization/
        |-- __init__.py
        +-- charts.py         # Visualizacao dinamica com Plotly
```

### Tecnologias Utilizadas

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.11+ |
| Framework LLM | LangChain + LangGraph |
| LLM | OpenAI GPT-4o-mini / Google Gemini 2.5 Flash |
| Banco de Dados | SQLite |
| Frontend | Streamlit |
| Visualizacao | Plotly Express |

---

## Fluxo do Agente

O agente SQL utiliza um StateGraph do LangGraph com os seguintes nos:

### 1. List Tables
Identifica todas as tabelas disponiveis no banco de dados.

### 2. Get Schema
Carrega o schema (DDL) das tabelas para fornecer contexto ao LLM.

### 3. Generate Query
O LLM traduz a pergunta em linguagem natural para uma query SQL valida.

### 4. Execute Query
Executa a query no banco SQLite.

### 5. Error Handler (Condicional)
Se a query falhar:
- Analisa o erro
- Corrige a query usando o LLM
- Tenta novamente (maximo 3 tentativas)

### 6. Formulate Response
Converte os resultados da query em uma resposta em linguagem natural.

### Diagrama de Fluxo

```
Pergunta do Usuario
        |
        v
+---------------+
| List Tables   |
+-------+-------+
        |
        v
+---------------+
| Get Schema    |
+-------+-------+
        |
        v
+---------------+
| Generate Query|
+-------+-------+
        |
        v
+---------------+
| Execute Query |
+-------+-------+
        |
    Erro? ----Sim----> Tentativas < 3? ----Sim----> Corrigir Query
        |                    |                            |
       Nao                  Nao                           |
        |                    |                            |
        v                    v                            |
+------------------+  +------------------+                |
|Formular Resposta |  |Resposta de Erro  |                |
+--------+---------+  +--------+---------+                |
         |                     |                          |
         +----------+----------+                          |
                    |                                     |
                    v                                     |
            Retornar ao Frontend <------------------------+
```

---

## Exemplos de Consultas

### Consultas Testadas

| Pergunta | Descricao |
|----------|-----------|
| "Quantos clientes existem no banco?" | Retorna contagem total de clientes |
| "Liste os 5 estados com mais clientes" | Ranking de estados por numero de clientes |
| "Qual o valor total de compras por categoria?" | Agregacao por categoria com grafico |
| "Quantas reclamacoes nao foram resolvidas?" | Filtro por status de resolucao |
| "Qual o ticket medio por canal de venda?" | Calculo de media agrupado |
| "Quais clientes compraram mais de 5 vezes?" | Filtro por frequencia de compra |

### Tipos de Visualizacao

O sistema detecta automaticamente o melhor tipo de grafico:

- **Grafico de Barras**: Dados categoricos com valores numericos (ate 15 itens)
- **Grafico de Pizza**: Distribuicoes simples (ate 6 itens)
- **Grafico de Linha**: Series temporais
- **Histograma**: Distribuicao de valores numericos
- **Tabela**: Fallback para dados complexos

---

## Sugestoes de Melhorias

### Curto Prazo

1. **Cache de Respostas**: Implementar cache para consultas repetidas usando Redis ou SQLite.

2. **Persistencia de Historico**: Salvar historico de conversas em banco de dados para retomada posterior.

3. **Validacao de SQL**: Adicionar camada de validacao para prevenir injecao de SQL e queries destrutivas.

4. **Testes Automatizados**: Implementar testes unitarios para o agente e visualizacoes.

### Medio Prazo

5. **API REST**: Expor funcionalidade via FastAPI para integracao com outros sistemas.

6. **Multiplos Bancos**: Suportar conexao com PostgreSQL, MySQL alem de SQLite.

7. **Exportacao de Dados**: Permitir download dos resultados em CSV, Excel ou PDF.

8. **Modo Socratico**: Adicionar modo onde o assistente faz perguntas clarificadoras antes de executar queries complexas.

### Longo Prazo

9. **RAG com Documentacao**: Integrar documentacao do schema para respostas mais contextualizadas.

10. **Dashboards Automaticos**: Gerar dashboards automaticos baseados em perguntas frequentes.

11. **Suporte a Voz**: Adicionar entrada por voz e leitura de respostas.

12. **Multi-tenant**: Suportar multiplos usuarios com bancos de dados isolados.

---

## Banco de Dados

O banco SQLite (`anexo_desafio_1.db`) contem as seguintes tabelas:

| Tabela | Colunas |
|--------|---------|
| clientes | id, nome, email, idade, cidade, estado, profissao, genero |
| compras | id, cliente_id, data_compra, valor, categoria, canal |
| suporte | id, cliente_id, data_contato, tipo_contato, resolvido, canal |
| campanhas_marketing | id, cliente_id, nome_campanha, data_envio, canal, interagiu |

---

## Licenca

Este projeto foi desenvolvido como parte de um desafio tecnico.
