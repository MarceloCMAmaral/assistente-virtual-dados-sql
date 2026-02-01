"""
Assistente Virtual de Dados - Streamlit Application

A chatbot that answers natural language questions by querying a SQLite database.
"""
import streamlit as st
from src.agent import run_agent, get_llm
from src.agent.llm import get_available_providers
from src.database import get_db_info
from src.visualization import display_data
from src.config import Config


# Page configuration
st.set_page_config(
    page_title="Assistente Virtual de Dados",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
    }
    .step-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 3px solid #4CAF50;
        padding-left: 1rem;
        background-color: #f0f2f6;
        border-radius: 0 5px 5px 0;
    }
    .sql-code {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 5px;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = Config.LLM_PROVIDER


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.header("Configuracoes")
        
        # LLM Provider selector
        available_providers = get_available_providers()
        
        if not available_providers:
            st.error("Nenhuma API key configurada!")
            st.info("Configure OPENAI_API_KEY ou GOOGLE_API_KEY no arquivo .env")
            return False
        
        provider_labels = {
            "openai": "OpenAI (GPT-4o-mini)",
            "gemini": "Google Gemini",
        }
        
        selected_provider = st.selectbox(
            "Provedor LLM",
            options=available_providers,
            format_func=lambda x: provider_labels.get(x, x),
            index=available_providers.index(st.session_state.llm_provider) 
                  if st.session_state.llm_provider in available_providers else 0,
        )
        st.session_state.llm_provider = selected_provider
        
        st.divider()
        
        # Database Info
        st.header("Banco de Dados")
        
        try:
            db_info = get_db_info()
            st.success(f"Conectado: {Config.DATABASE_PATH}")
            
            with st.expander("Tabelas Disponiveis"):
                for table in db_info["tables"]:
                    st.markdown(f"- `{table}`")
            
            with st.expander("Schema Completo"):
                st.code(db_info["schema"], language="sql")
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")
            return False
        
        st.divider()
        
        # Clear history button
        if st.button("Limpar Historico", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        
        # Example questions
        st.header("Exemplos")
        examples = [
            "Quantos clientes existem no banco?",
            "Liste os 5 estados com mais clientes",
            "Qual o valor total de compras por categoria?",
            "Quantas reclamacoes nao foram resolvidas?",
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{example}", use_container_width=True):
                st.session_state.pending_question = example
                st.rerun()
        
        return True


def render_chat_history():
    """Render the chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant":
                # Show reasoning steps
                if "steps" in message and message["steps"]:
                    with st.expander("Ver raciocinio do agente"):
                        for step in message["steps"]:
                            st.markdown(step)
                
                # Show query
                if "query" in message and message["query"]:
                    with st.expander("Ver query SQL"):
                        st.code(message["query"], language="sql")
                
                # Show data visualization
                if "query_result" in message and message["query_result"]:
                    with st.expander("Ver dados", expanded=True):
                        display_data(message["query_result"], query=message.get("query"))


def process_question(question: str):
    """Process a question and generate a response."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user"):
        st.markdown(question)
    
    with st.chat_message("assistant"):
        with st.status("Analisando sua pergunta...", expanded=True) as status:
            try:
                # Run the agent
                result = run_agent(
                    question=question,
                    llm_provider=st.session_state.llm_provider,
                )
                
                # Show steps in real-time
                for step in result.get("steps", []):
                    st.markdown(step)
                
                status.update(label="Analise completa!", state="complete")
                
            except Exception as e:
                status.update(label="Erro na analise", state="error")
                st.error(f"Erro: {str(e)}")
                result = {
                    "final_answer": f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}",
                    "steps": [],
                    "query": "",
                    "query_result": "",
                    "error": str(e),
                }
        
        # Show final answer
        st.markdown(result.get("final_answer", ""))
        
        # Show query if available
        if result.get("query"):
            with st.expander("Ver query SQL"):
                st.code(result["query"], language="sql")
        
        # Show data visualization if available
        if result.get("query_result"):
            with st.expander("Ver dados", expanded=True):
                display_data(result["query_result"], query=result.get("query"))
        
        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("final_answer", ""),
            "steps": result.get("steps", []),
            "query": result.get("query", ""),
            "query_result": result.get("query_result", ""),
        })


def main():
    """Main application entry point."""
    init_session_state()
    
    # Title
    st.title("Assistente Virtual de Dados")
    st.caption("Faca perguntas em linguagem natural sobre seus dados")
    
    # Render sidebar
    is_configured = render_sidebar()
    
    if not is_configured:
        st.warning("Configure as variaveis de ambiente para comecar.")
        st.info("""
        1. Copie o arquivo `.env.example` para `.env`
        2. Adicione sua chave de API (OpenAI ou Google)
        3. Reinicie a aplicacao
        """)
        return
    
    # Render chat history
    render_chat_history()
    
    # Check for pending question from example buttons
    if hasattr(st.session_state, "pending_question"):
        question = st.session_state.pending_question
        del st.session_state.pending_question
        process_question(question)
    
    # Chat input
    if prompt := st.chat_input("Faca sua pergunta sobre os dados..."):
        process_question(prompt)


if __name__ == "__main__":
    main()
