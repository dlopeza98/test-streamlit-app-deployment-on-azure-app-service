import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from dotenv import load_dotenv

load_dotenv()


def list_search_indexes():
    service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    api_key = os.getenv("SEARCH_API_KEY")

    if not service_endpoint or not api_key:
        raise ValueError(
            "Please set the SEARCH_SERVICE_ENDPOINT and SEARCH_API_KEY environment variables."
        )

    client = SearchIndexClient(
        endpoint=service_endpoint, credential=AzureKeyCredential(api_key)
    )
    indexes = client.list_indexes()

    print("Available search indexes:")
    for index in indexes:
        print(index.name)


if __name__ == "__main__":
    list_search_indexes()
