# ----------------------------------------------
# 1. Create AI Project Client
# ----------------------------------------------
import os

import pandas as pd
from azure.ai.evaluation import GroundednessEvaluator, evaluate
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from chat_with_pdf import chat_with_pdf

# load environment variables from the .env file at the root of this repo
from dotenv import load_dotenv

load_dotenv()

# create a project client using environment variables loaded from the .env file
project = AIProjectClient.from_connection_string(
    conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
    credential=DefaultAzureCredential(),
)

connection = project.connections.get_default(
    connection_type=ConnectionType.AZURE_OPEN_AI, include_credentials=True
)

# ----------------------------------------------
# 2. Define Evaluator Model to use
# ----------------------------------------------
evaluator_model = {
    "azure_endpoint": connection.endpoint_url,
    "azure_deployment": os.environ["EVALUATION_MODEL"],
    "api_version": "2024-06-01",
    "api_key": connection.key,
}

groundedness = GroundednessEvaluator(evaluator_model)


# ----------------------------------------------
# 3. Create Eval Wrapper Function for Query
# ----------------------------------------------
def evaluate_chat_with_pdf(query):
    response = chat_with_pdf(messages=[{"role": "user", "content": query}])
    return {
        "response": response["message"].content,
        "context": response["context"]["grounding_data"],
    }


# ----------------------------------------------
# 4. Run the Evaluation
#    View Results Locally (Saved as JSON)
#    Get Link to View Results in Foundry Portal
#    NOTE:
#    Evaluation takes more tokens
#    Try to increase Rate limit (Tokens per minute)
#    Script should handle limit errors if needed
# ----------------------------------------------
# Evaluate must be called inside of __main__, not on import
if __name__ == "__main__":
    import contextlib
    import multiprocessing
    from pathlib import Path

    # workaround for multiprocessing issue on linux
    from pprint import pprint

    from config import ASSET_PATH

    with contextlib.suppress(RuntimeError):
        multiprocessing.set_start_method("spawn", force=True)

    # run evaluation with a dataset and target function, log to the project
    result = evaluate(
        data=Path(ASSET_PATH) / "chat_eval_data.jsonl",
        target=evaluate_chat_with_pdf,
        evaluation_name="evaluate_chat_with_pdf",
        evaluators={
            "groundedness": groundedness,
        },
        evaluator_config={
            "default": {
                "query": {"${data.query}"},
                "response": {"${target.response}"},
                "context": {"${target.context}"},
            }
        },
        azure_ai_project=project.scope,
        output_path="./myevalresults.json",
    )

    tabular_result = pd.DataFrame(result.get("rows"))

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")

# ----------------------------------------------
# Run the Evaluation using this command
#    python evaluate_chat_with_pdf.py
#
# You should see something like this:

"""
Starting prompt flow service...
Start prompt flow service on 127.0.0.1:23333, version: 1.16.2.
You can stop the prompt flow service with the following command:'pf service stop'.

You can view the traces in local from http://127.0.0.1:23333/v1.0/ui/traces/?#run=main_evaluate_chat_with_pdf_rxna_3r9_20241216_163719_733780
[2024-12-16 16:37:42 +0000][promptflow._sdk._orchestrator.run_submitter][INFO] - Submitting run main_evaluate_chat_with_pdf_rxna_3r9_20241216_163719_733780, log path: /home/vscode/.promptflow/.runs/main_evaluate_chat_with_pdf_rxna_3r9_20241216_163719_733780/logs.txt
Response: {'content': 'The main topic of the document is about strategies for essay writing. It covers various techniques and tips to improve essay writing skills.', 'role': 'assistant'}
...
"""

# This is what a rate limit error looks like:

"""
[2024-12-16 16:44:07 +0000][promptflow.core._prompty_utils][ERROR] - Exception occurs: RateLimitError: Error code: 429 - {'error': {'code': '429', 'message': 'Requests to the ChatCompletions_Create Operation under Azure OpenAI API version 2024-06-01 have exceeded token rate limit of your current AIServices S0 pricing tier. Please retry after 60 seconds. Please contact Azure support service if you would like to further increase the default rate limit.'}}
[2024-12-16 16:44:07 +0000][promptflow.core._prompty_utils][WARNING] - RateLimitError #2, Retry-After=60, Back off 60.0 seconds for retry.
"""

# This is what the final result looks like

"""
======= Run Summary =======

Run name: "azure_ai_evaluation_evaluators_common_base_eval_asyncevaluatorbase_rvrjml8t_20241216_164205_696721"
Run status: "Completed"
Start time: "2024-12-16 16:42:05.695977+00:00"
Duration: "0:03:06.490785"
Output path: "/home/vscode/.promptflow/.runs/azure_ai_evaluation_evaluators_common_base_eval_asyncevaluatorbase_rvrjml8t_20241216_164205_696721"

======= Combined Run Summary (Per Evaluator) =======

{
    "groundedness": {
        "status": "Completed",
        "duration": "0:03:06.490785",
        "completed_lines": 13,
        "failed_lines": 0,
        "log_path": "/home/vscode/.promptflow/.runs/azure_ai_evaluation_evaluators_common_base_eval_asyncevaluatorbase_rvrjml8t_20241216_164205_696721"
    }
}

====================================================

Evaluation results saved to "/workspaces/learns-azure-ai-foundry/src/api/myevalresults.json".

'-----Summarized Metrics-----'
{'groundedness.gpt_groundedness': 1.4615384615384615,
 'groundedness.groundedness': 1.4615384615384615}
'-----Tabular Result-----'
                                     outputs.response  ... line_number
0   The main topic of the document is about strateg...  ...           0
1   The document provides various techniques and ti...  ...           1
2   The document discusses the importance of struct...  ...           2
3   The document highlights the significance of pro...  ...           3
4   The document offers tips on how to improve essa...  ...           4
5   The document emphasizes the need for clear and ...  ...           5
6   The document suggests ways to enhance the quali...  ...           6
7   The document provides examples of effective ess...  ...           7
8   The document discusses common mistakes to avoid...  ...           8
9   The document outlines the steps to write a succ...  ...           9
10  The document offers advice on how to edit and p...  ...          10
11  The document provides resources for further rea...  ...          11
12  The document concludes with a summary of key po...  ...          12

[13 rows x 8 columns]
('View evaluation results in AI Studio: '
 'https://ai.azure.com/build/evaluation/XXXXXXX?wsid=/subscriptions/XXXXXXXX/resourceGroups/ninarasi-ragchat-rg/providers/Microsoft.MachineLearningServices/workspaces/ninarasi-ragchat-v1')
"""

# ----------------------------------------------
