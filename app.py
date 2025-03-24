import os
import tempfile

import streamlit as st

from utilities.az_login import az_login
from utilities.chat_with_pdf import ask_ai_with_pdf_context
from utilities.create_search_index import index_pdf_document
from utilities.delete_search_index import delete_search_index

# Configuración de la interfaz
st.set_page_config(page_title="Chat con PDF", layout="wide")
st.markdown(
    """
    <link rel="icon" href="static/bpt-logo-horizontal.webp" type="image/webp">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .chat-bubble {
        display: flex;
        align-items: center;
        border-radius: 1.5rem;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        color: white;
        font-size: 16px;
    }
    .chat-user {
        background-color: #0077B6;
        justify-content: flex-end;
    }
    .chat-assistant {
        background-color: #3a0ca3;
        justify-content: flex-start;
    }
    .chat-icon {
        font-size: 24px;
        margin: 0 0.5rem;
    }
    .chat-text {
        max-width: 85%;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .header-logo img {
        max-height: 60px;
    }
    .custom-caption {
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    .scrollable-chat {
        max-height: 500px;
        overflow-y: auto;
        padding-right: 10px;
    }
    .left-panel-box {
        border: 1px solid #ccc;
        padding: 1rem;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Encabezado con logo a la derecha
st.markdown(
    """
<div class="header-container">
    <h1>🤖 Chat Inteligente con tus PDFs</h1>
    <div class="header-logo">
        <a href="https://bpt.com.co/" target="_blank">
            <img src="https://bpt.com.co/wp-content/uploads/2023/06/bpt-logo-horizontal.webp" alt="BPT Logo">
        </a>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="custom-caption">
    Sube un documento PDF y conversa directamente con su contenido usando inteligencia artificial. Desarrollado por <a href="https://www.linkedin.com/in/camilo-alejandro-v%C3%A9lez-medina-1b447a144/" target="_blank">Camilo Alejandro Vélez Medina</a> y <a href="https://www.linkedin.com/in/davidalopeza/" target="_blank">David Alejandro López Atehortúa</a>.<br>
</div>
""",
    unsafe_allow_html=True,
)

# Autenticación Azure (solo una vez al iniciar la app)
if "azure_logged_in" not in st.session_state:
    with st.spinner("Autenticando con Azure..."):
        try:
            az_login()
            st.session_state.azure_logged_in = True
        except Exception as e:
            st.error(f"Error al autenticar con Azure: {e}")

# Estructura en columnas con separación visual
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    with st.container(border=True):
        st.subheader("📄 Carga de documento PDF")
        uploaded_file = st.file_uploader(
            "Selecciona un archivo PDF", type=["pdf"], accept_multiple_files=False
        )

        if uploaded_file and st.button("✅ Cargar e indexar PDFs"):
            index_name = os.getenv("AISEARCH_INDEX_NAME")
            if not index_name:
                st.error("La variable de entorno AISEARCH_INDEX_NAME no está definida.")
            else:
                st.session_state.pdf_ready = True

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    temp_pdf_path = tmp.name

                with st.spinner(f"Cargando e indexando '{uploaded_file.name}'..."):
                    try:
                        index_pdf_document(
                            index_name=index_name, pdf_path=temp_pdf_path
                        )
                        st.success(
                            f"'{uploaded_file.name}' cargado e indexado exitosamente."
                        )
                    except Exception as e:
                        st.error(f"Error al indexar '{uploaded_file.name}': {e}")
                        st.session_state.pdf_ready = False

        st.divider()
        st.subheader("🗑️ Eliminar base de conocimiento de IA")
        if st.button("Eliminar PDFs"):
            try:
                index_name = os.getenv("AISEARCH_INDEX_NAME")
                delete_search_index(index_name)
                st.success(f"Índice '{index_name}' eliminado correctamente.")
                st.session_state.pdf_ready = False
            except Exception as e:
                st.error(f"Error al eliminar el índice: {e}")

with right_col:
    if st.session_state.get("pdf_ready"):
        st.subheader("💬 Chat con tus PDFs")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""

        with st.form(key="chat_form"):
            query = st.text_input(
                "Escribe tu pregunta:",
                placeholder="¿Qué dice el documento sobre...?",
                key="query_input",
            )
            submit = st.form_submit_button("Enviar pregunta")

            if submit and query:
                messages = [{"role": "user", "content": query}]
                try:
                    with st.spinner("Consultando al modelo de lenguaje..."):
                        response = ask_ai_with_pdf_context(messages)
                        st.session_state.chat_history.append(("Usuario", query))
                        st.session_state.chat_history.append(
                            ("Asistente", response["message"])
                        )
                except Exception as e:
                    st.error(f"Ocurrió un error al consultar: {e}")

        st.subheader("📒 Historial de conversación")
        st.markdown("<div class='scrollable-chat'>", unsafe_allow_html=True)
        for role, msg in reversed(st.session_state.chat_history):
            css_class = "chat-user" if role == "Usuario" else "chat-assistant"
            icon_html = (
                f"<div class='chat-icon'>{'🧑‍💼' if role == 'Usuario' else '🤖'}</div>"
            )
            text_html = (
                f"<div class='chat-text'><strong>{role}:</strong><br>{msg}</div>"
            )

            if role == "Usuario":
                st.markdown(
                    f"""
                    <div class="chat-bubble {css_class}">
                        {text_html}{icon_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="chat-bubble {css_class}">
                        {icon_html}{text_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Por favor sube e indexa al menos un PDF para habilitar el chat.")
