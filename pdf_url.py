import streamlit as st
import typer
from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2
import os
from dotenv import load_dotenv

load_dotenv()

# Configure API keys
groq_api_key = os.getenv("GROQ_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
os.environ["GROQ_API"] = groq_api_key
os.environ["OPENAI_API_KEY"] = openai_api_key

# Database configuration
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Initialize chat history if not present
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("PDF Chat Assistant")

def safe_init_knowledge_base(pdf_url):
    try:
        knowledge_base = PDFUrlKnowledgeBase(
            urls=[pdf_url],
            vector_db=PgVector2(collection="recipes", db_url=db_url)
        )
        knowledge_base.load(recreate=True, upsert=True)
        return knowledge_base
    except Exception as e:
        st.error(f"Error initializing knowledge base: {str(e)}")
        return None

# URL input and initialization
with st.sidebar:
    st.header("Configuration")

    st.markdown("---")
    
    # Add developer credit with custom styling
    st.markdown("""
        <div style='background-color: #f0f2f6; 
                    padding: 20px; 
                    border-radius: 10px; 
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1)'>
            <p style='margin:0; 
                      font-size: 1.1em; 
                      color: #0f52ba;'>
                Developed with ❤️ by
            </p>
            <p style='margin:0; 
                      font-size: 1.4em; 
                      font-weight: bold; 
                      background: linear-gradient(45deg, #1e3799, #0984e3);
                      -webkit-background-clip: text;
                      -webkit-text-fill-color: transparent;'>
                Sunil Modi
            </p>
        </div>
    """, unsafe_allow_html=True)


    pdf_url = st.text_input(
        "Enter PDF URL:",
        "https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"
    )
    
    if st.button("Initialize System"):
        with st.spinner("Loading PDF..."):
            knowledge_base = safe_init_knowledge_base(pdf_url)
            if knowledge_base:
                st.session_state['knowledge_base'] = knowledge_base
                storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)
                
                assistant = Assistant(
                    user_id="user",
                    knowledge_base=knowledge_base,
                    storage=storage,
                    show_tool_calls=True,
                    search_knowledge=True,
                    read_chat_history=True
                )
                
                st.session_state['assistant'] = assistant
                st.success("✅ System initialized!")

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.pop('assistant', None)
        st.session_state.pop('knowledge_base', None)
        st.success("Chat cleared!")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if 'assistant' in st.session_state:
    if prompt := st.chat_input("Ask your question about the PDF"):
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate and display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                for response_chunk in st.session_state['assistant'].chat(prompt):
                    full_response += response_chunk
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
else:
    st.info("👈 Please initialize the system first by loading a PDF in the sidebar")

# Display system status in sidebar
with st.sidebar:
    st.header("System Status")
    if 'assistant' in st.session_state:
        st.success("System is ready")
    else:
        st.warning("System needs initialization")