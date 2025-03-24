import os
import subprocess

from dotenv import load_dotenv

load_dotenv()


def az_login():
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")

    if not client_id or not client_secret or not tenant_id:
        raise ValueError(
            "Please set the AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID environment variables."
        )

    subprocess.run(
        [
            "az",
            "login",
            "--service-principal",
            "--username",
            client_id,
            "--password",
            client_secret,
            "--tenant",
            tenant_id,
        ],
        check=True,
    )
