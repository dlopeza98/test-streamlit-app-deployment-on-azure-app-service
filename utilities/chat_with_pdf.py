import os
from pathlib import Path

from azure.ai.inference.prompts import PromptTemplate
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from opentelemetry import trace
from utilities.config import ASSET_PATH, get_logger

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


def ask_ai_with_pdf_context(messages: list, context: dict = None) -> dict:
    """
    Realiza una consulta a la IA usando documentos indexados en Azure Search (solo PDFs).
    """
    if context is None:
        context = {}

    # Crear cliente de proyecto
    project = AIProjectClient.from_connection_string(
        conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
        credential=DefaultAzureCredential(),
    )
    chat = project.inference.get_chat_completions_client()

    # Crear cliente de búsqueda solo para PDFs
    pdf_search_client = SearchClient(
        endpoint=os.environ["SEARCH_SERVICE_ENDPOINT"],
        index_name=os.environ["AISEARCH_INDEX_NAME"],
        credential=AzureKeyCredential(os.environ["SEARCH_API_KEY"]),
    )

    # Extraer última pregunta del usuario
    query = messages[-1]["content"]

    # Buscar en índice de PDF
    pdf_documents = []
    for result in pdf_search_client.search(query):
        pdf_documents.append({"title": result["title"], "content": result["content"]})

    # Generar prompt contextualizado solo con documentos PDF
    grounded_prompt = PromptTemplate.from_prompty(
        Path(ASSET_PATH) / "grounded_chat.prompty"
    )
    system_message = grounded_prompt.create_messages(
        documents=pdf_documents, context=context
    )

    # Llamar al modelo
    response = chat.complete(
        model=os.environ["CHAT_MODEL"],
        messages=system_message + messages,
        **grounded_prompt.parameters,
    )

    return {
        "message": response.choices[0].message.content,
        "context": context,
    }
