"""
SQL Agent using LangGraph StateGraph.

This module implements a custom SQL agent that:
1. Lists available tables
2. Gets schema for relevant tables
3. Generates SQL queries from natural language
4. Executes queries with auto-correction on errors
5. Formats results into natural language responses
"""
from typing import TypedDict, Annotated, Literal
from operator import add
from langgraph.graph import StateGraph, END

from src.config import Config
from src.database.connection import get_database, get_db_info
from src.agent.llm import get_llm
from src.agent.prompts import (
    QUERY_GENERATION_PROMPT,
    QUERY_CORRECTION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
)


class SQLAgentState(TypedDict):
    """State for the SQL Agent workflow."""
    question: str
    tables: list[str]
    schema: str
    query: str
    query_result: str
    error: str
    retry_count: int
    final_answer: str
    steps: Annotated[list[str], add]  # Accumulates steps for transparency
    llm_provider: str


def list_tables(state: SQLAgentState) -> dict:
    """Node: List available database tables."""
    db = get_database()
    tables = db.get_usable_table_names()
    
    step = f"📋 **Tabelas encontradas:** {', '.join(tables)}"
    
    return {
        "tables": tables,
        "steps": [step],
    }

def filter_tables(state: SQLAgentState) -> dict:
    """Node: Filter tables based on relevance to the question."""
    llm = get_llm(state.get("llm_provider"))
    question = state["question"]
    all_tables = state["tables"]
    
    # If there are few tables (e.g., < 2), don't waste tokens on filtering
    if len(all_tables) <= 2:
        return {"tables": all_tables}

    from src.agent.prompts import TABLE_SELECTION_PROMPT
    
    prompt = TABLE_SELECTION_PROMPT.format(
        question=question,
        table_list=", ".join(all_tables)
    )
    
    response = llm.invoke(prompt)
    selected_tables_str = response.content.strip()
    
    # Parse the response string into a list
    selected_tables = [t.strip() for t in selected_tables_str.split(',')]
    
    # Simple validation to ensure tables exist
    valid_tables = [t for t in selected_tables if t in all_tables]
    
    # Fallback: If the LLM hallucinates and doesn't return anything valid, use all
    if not valid_tables:
        valid_tables = all_tables
        
    step = f"🕵️ **Tabelas selecionadas:** {', '.join(valid_tables)}"
    
    return {
        "tables": valid_tables, # Updates state with only the relevant tables
        "steps": [step]
    }

def get_schema(state: SQLAgentState) -> dict:
    """Node: Get schema for all tables."""
    db = get_database()
    tables = state.get("tables", [])
    
    schema = db.get_table_info(table_names=tables)
    step = "📊 **Schema carregado com sucesso**"
    
    return {
        "schema": schema,
        "steps": [step],
    }


def generate_query(state: SQLAgentState) -> dict:
    """Node: Generate SQL query from the question."""
    llm = get_llm(state.get("llm_provider"))
    
    prompt = QUERY_GENERATION_PROMPT.format(
        question=state["question"],
        schema=state["schema"],
        limit=Config.DEFAULT_QUERY_LIMIT,
    )
    
    response = llm.invoke(prompt)
    query = response.content.strip()
    
    # Clean up query (remove markdown code blocks if present)
    if query.startswith("```sql"):
        query = query[6:]
    if query.startswith("```"):
        query = query[3:]
    if query.endswith("```"):
        query = query[:-3]
    query = query.strip()
    
    step = f"🔍 **Query gerada:**\n```sql\n{query}\n```"
    
    return {
        "query": query,
        "steps": [step],
    }


def execute_query(state: SQLAgentState) -> dict:
    """Node: Execute the SQL query."""
    db = get_database()
    query = state["query"]
    
    try:
        result = db.run(query)
        return {
            "query_result": result,
            "error": "",
            "steps": ["✅ **Query executada com sucesso**"],
        }
    except Exception as e:
        retry_count = state.get("retry_count", 0) + 1
        error_msg = str(e)
        
        return {
            "query_result": "",
            "error": error_msg,
            "retry_count": retry_count,
            "steps": [f"❌ **Erro na execução (tentativa {retry_count}/3):** {error_msg}"],
        }


def correct_query(state: SQLAgentState) -> dict:
    """Node: Correct SQL query based on error."""
    llm = get_llm(state.get("llm_provider"))
    
    prompt = QUERY_CORRECTION_PROMPT.format(
        query=state["query"],
        error=state["error"],
        schema=state["schema"],
    )
    
    response = llm.invoke(prompt)
    corrected_query = response.content.strip()
    
    # Clean up query
    if corrected_query.startswith("```sql"):
        corrected_query = corrected_query[6:]
    if corrected_query.startswith("```"):
        corrected_query = corrected_query[3:]
    if corrected_query.endswith("```"):
        corrected_query = corrected_query[:-3]
    corrected_query = corrected_query.strip()
    
    step = f"🔧 **Query corrigida:**\n```sql\n{corrected_query}\n```"
    
    return {
        "query": corrected_query,
        "steps": [step],
    }


def formulate_response(state: SQLAgentState) -> dict:
    """Node: Formulate natural language response."""
    llm = get_llm(state.get("llm_provider"))
    
    # Check if there was an error that couldn't be corrected
    if state.get("error") and state.get("retry_count", 0) >= Config.MAX_RETRY_ATTEMPTS:
        return {
            "final_answer": f"Desculpe, não foi possível executar a consulta após {Config.MAX_RETRY_ATTEMPTS} tentativas. "
                           f"Último erro: {state['error']}",
            "steps": ["⚠️ **Não foi possível completar a consulta**"],
        }
    
    prompt = RESPONSE_GENERATION_PROMPT.format(
        question=state["question"],
        query=state["query"],
        result=state["query_result"],
    )
    
    response = llm.invoke(prompt)
    answer = response.content.strip()
    
    return {
        "final_answer": answer,
        "steps": ["💬 **Resposta formulada**"],
    }


def should_retry(state: SQLAgentState) -> Literal["correct", "respond"]:
    """Conditional edge: Decide whether to retry or respond."""
    if state.get("error") and state.get("retry_count", 0) < Config.MAX_RETRY_ATTEMPTS:
        return "correct"
    return "respond"


def build_sql_agent() -> StateGraph:
    """Build and compile the SQL Agent graph."""
    workflow = StateGraph(SQLAgentState)
    
    # Add nodes
    workflow.add_node("list_tables", list_tables)
    workflow.add_node("filter_tables", filter_tables)
    workflow.add_node("get_schema", get_schema)
    workflow.add_node("generate_query", generate_query)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("correct_query", correct_query)
    workflow.add_node("formulate_response", formulate_response)
    
    # Set entry point
    workflow.set_entry_point("list_tables")
    
    # Add edges
    workflow.add_edge("list_tables", "filter_tables")
    workflow.add_edge("filter_tables", "get_schema")
    workflow.add_edge("get_schema", "generate_query")
    workflow.add_edge("generate_query", "execute_query")
    workflow.add_conditional_edges(
        "execute_query",
        should_retry,
        {
            "correct": "correct_query",
            "respond": "formulate_response",
        }
    )
    workflow.add_edge("correct_query", "execute_query")
    workflow.add_edge("formulate_response", END)
    
    return workflow.compile()


# Cached agent instance
_agent = None


def get_agent():
    """Get or create the SQL agent."""
    global _agent
    if _agent is None:
        _agent = build_sql_agent()
    return _agent


def run_agent(question: str, llm_provider: str = None) -> dict:
    """
    Execute SQL agent with a natural language question.
    
    Args:
        question: Natural language question about the data.
        llm_provider: LLM provider to use ("openai" or "gemini").
                      Defaults to Config.LLM_PROVIDER.
    
    Returns:
        dict with keys:
            - question: str (original question)
            - query: str (SQL generated)
            - query_result: str (raw result)
            - final_answer: str (natural language response)
            - steps: List[str] (reasoning steps)
            - error: str (if any)
    """
    agent = get_agent()
    
    initial_state = {
        "question": question,
        "tables": [],
        "schema": "",
        "query": "",
        "query_result": "",
        "error": "",
        "retry_count": 0,
        "final_answer": "",
        "steps": [],
        "llm_provider": llm_provider or Config.LLM_PROVIDER,
    }
    
    result = agent.invoke(initial_state)
    
    return {
        "question": result.get("question", question),
        "query": result.get("query", ""),
        "query_result": result.get("query_result", ""),
        "final_answer": result.get("final_answer", ""),
        "steps": result.get("steps", []),
        "error": result.get("error", ""),
    }
