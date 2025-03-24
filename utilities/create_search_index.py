import os

import fitz  # PyMuPDF
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from utilities.config import get_logger

logger = get_logger(__name__)


def index_pdf_document(index_name: str, pdf_path: str):
    # Inicializar clientes
    project = AIProjectClient.from_connection_string(
        conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
        credential=DefaultAzureCredential(),
    )
    embeddings = project.inference.get_embeddings_client()
    search_connection = project.connections.get_default(
        connection_type=ConnectionType.AZURE_AI_SEARCH, include_credentials=True
    )
    index_client = SearchIndexClient(
        endpoint=search_connection.endpoint_url,
        credential=AzureKeyCredential(key=search_connection.key),
    )

    def create_index_definition(model: str) -> SearchIndex:
        dimensions = 3072 if model == "text-embedding-3-large" else 1536
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="filepath", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="url", type=SearchFieldDataType.String),
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dimensions,
                vector_search_profile_name="myHnswProfile",
            ),
        ]
        return SearchIndex(
            name=index_name,
            fields=fields,
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="default",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[SemanticField(field_name="content")],
                        ),
                    )
                ]
            ),
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="myHnsw",
                        kind=VectorSearchAlgorithmKind.HNSW,
                        parameters=HnswParameters(
                            m=4,
                            ef_construction=1000,
                            ef_search=1000,
                            metric=VectorSearchAlgorithmMetric.COSINE,
                        ),
                    ),
                    ExhaustiveKnnAlgorithmConfiguration(
                        name="myExhaustiveKnn",
                        kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                        parameters=ExhaustiveKnnParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE,
                        ),
                    ),
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile", algorithm_configuration_name="myHnsw"
                    ),
                    VectorSearchProfile(
                        name="myExhaustiveKnnProfile",
                        algorithm_configuration_name="myExhaustiveKnn",
                    ),
                ],
            ),
        )

    # Eliminar índice anterior si existe
    try:
        index_client.get_index(index_name)
        index_client.delete_index(index_name)
        logger.info(f"🗑️  Índice '{index_name}' eliminado.")
    except Exception:
        pass

    # Crear nuevo índice
    index_definition = create_index_definition(os.environ["EMBEDDINGS_MODEL"])
    index_client.create_index(index_definition)

    # Extraer texto y vectorizar
    doc = fitz.open(pdf_path)
    content = "".join(page.get_text() for page in doc)
    doc_id = os.path.basename(pdf_path).replace(".pdf", "").replace(" ", "_")
    embedding = embeddings.embed(input=content, model=os.environ["EMBEDDINGS_MODEL"])
    document = [
        {
            "id": doc_id,
            "content": content,
            "filepath": pdf_path,
            "title": doc_id,
            "url": f"/documents/{doc_id.lower()}",
            "contentVector": embedding.data[0].embedding,
        }
    ]

    # Subir documentos
    search_client = SearchClient(
        endpoint=search_connection.endpoint_url,
        index_name=index_name,
        credential=AzureKeyCredential(key=search_connection.key),
    )
    search_client.upload_documents(document)
    logger.info(f"✅ Documento '{pdf_path}' indexado en '{index_name}'")
