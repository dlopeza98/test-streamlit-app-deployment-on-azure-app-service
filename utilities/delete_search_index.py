import os
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from dotenv import load_dotenv

load_dotenv()


def delete_search_index(index_name):
    service_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    api_key = os.getenv("SEARCH_API_KEY")

    if not service_endpoint or not api_key:
        raise ValueError(
            "Please set the SEARCH_SERVICE_ENDPOINT and SEARCH_API_KEY environment variables."
        )

    client = SearchIndexClient(
        endpoint=service_endpoint, credential=AzureKeyCredential(api_key)
    )
    client.delete_index(index_name)
    print(f"Search index '{index_name}' deleted successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete-search-index.py <index-name>")
        sys.exit(1)

    index_name = sys.argv[1]
    delete_search_index(index_name)
