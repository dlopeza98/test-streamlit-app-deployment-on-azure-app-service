import os

import pandas as pd
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from config import get_logger

# initialize logging object
logger = get_logger(__name__)

# create a project client using environment variables loaded from the .env file
project = AIProjectClient.from_connection_string(
    conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
    credential=DefaultAzureCredential(),
)

# create a vector embeddings client that will be used to generate vector embeddings
embeddings = project.inference.get_embeddings_client()

# use the project client to get the default search connection
search_connection = project.connections.get_default(
    connection_type=ConnectionType.AZURE_AI_SEARCH, include_credentials=True
)

# Create a search index client using the search connection
index_client = SearchIndexClient(
    endpoint=search_connection.endpoint_url,
    credential=AzureKeyCredential(key=search_connection.key),
)

# Define Function To Create Search Index
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)


def create_product_index_definition(index_name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="name", type=SearchFieldDataType.String),
        SimpleField(name="price", type=SearchFieldDataType.Double),
        SearchableField(name="category", type=SearchFieldDataType.String),
        SearchableField(name="brand", type=SearchFieldDataType.String),
        SearchableField(name="description", type=SearchFieldDataType.String),
        SimpleField(
            name="quantity", type=SearchFieldDataType.Int32
        ),  # Add quantity field
    ]

    return SearchIndex(
        name=index_name,
        fields=fields,
    )


# Define Function To Add Documents To Index
def create_docs_from_csv(path: str) -> list[dict[str, any]]:
    df = pd.read_csv(path)
    df["id"] = df["id"].astype(str)  # Ensure the 'id' field is treated as a string
    docs = df.to_dict(orient="records")
    return docs


def create_index_from_csv(index_name, csv_file):
    try:
        index_definition = index_client.get_index(index_name)
        index_client.delete_index(index_name)
        logger.info(f"🗑️  Found existing index named '{index_name}', and deleted it")
    except Exception:
        pass

    index_definition = create_product_index_definition(index_name)
    index_client.create_index(index_definition)

    docs = create_docs_from_csv(path=csv_file)

    search_client = SearchClient(
        endpoint=search_connection.endpoint_url,
        index_name=index_name,
        credential=AzureKeyCredential(key=search_connection.key),
    )

    search_client.upload_documents(docs)
    logger.info(f"➕ Uploaded {len(docs)} documents to '{index_name}' index")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--index-name",
        type=str,
        help="index name to use when creating the product index",
        default=os.environ["PRODUCT_INDEX_NAME"],
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        help="path to CSV file for creating product index",
        default="assets/products.csv",
    )
    args = parser.parse_args()
    index_name = args.index_name
    csv_file = args.csv_file

    create_index_from_csv(index_name, csv_file)
