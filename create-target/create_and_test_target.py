import time
from typing import Any
import requests
import os
import sys
import csv

# Creates a target, runs a test, prints results
# Usage: $ python create_and_test_target.py

api_key = "***REPLACE_WITH_API_KEY_FOR_TARGET_UNDER_TEST***"
target_name = "REPLACE_WITH_YOUR_TARGET_NAME"
url = "REPLACE_WITH_URL"  # e.g. https://example-endpoint.aws.endpoints.huggingface.cloud.example.com

# Define the target

# e.g OPENAI target
# target = {
#     "model_type": "llm",
#     "dataset": "Bad Questions",
#     "target": target_name,
#     "preset": "openai",
#     "url": url,
#     "api_key": api_key,
#     "model_name": "gpt-3.5-turbo",
#     "headers": "Authorization: Bearer " + api_key,
#     "system_prompt": "Please answer the question: "
# }

# e.g HUGGINGFACE target
# target = {
#     "model_type": "llm",
#     "dataset": "Bad Questions",
#     "target": target_name,
#     "preset": "huggingface",
#     "url": url,
#     "api_key": api_key,
#     "headers": "Authorization: Bearer " + api_key,
#     "selector": "$[*].generated_text",
#     "request_template": "{\"inputs\": \"[INST] {system_prompt} {prompt} [/INST]\", \"parameters\": {\"temperature\": 0.001}}",
#     "system_prompt": "Please answer the question: "
# }

# e.g CUSTOM REST API target
target = {
    "model_type": "llm",
    "dataset": "Bad Questions",
    "target": target_name,
    "url": url,
    "api_key": api_key,
    "headers": "Authorization: Bearer " + api_key,
    "selector": "$[*].generated_text",
    "request_template": "{\"inputs\": \"[INST] {system_prompt} {prompt} [/INST]\", \"parameters\": {\"temperature\": 0.001}}",
    "system_prompt": "Please answer the question: "
}

# Authenticate
def authenticate() -> str:
    # Generate a bearer token. If you're already using the Mindgard CLI the easiest method is to reuse the CLI token
    # Assumes you have run the CLI once and logged in, generating a ~/.mindgard/token.txt
    config_folder = os.path.join(os.path.expanduser('~'), '.mindgard')

    with open(os.path.join(config_folder, "token.txt"), "r") as f:
        refresh_token = f.read().strip()
        access_token = (
            requests.post(
                "https://{}/oauth/token".format("login.sandbox.mindgard.ai"),
                data={
                    "grant_type": "refresh_token",
                    "client_id": "U0OT7yZLJ4GEyabar11BENeQduu4MaNO",
                    "audience": "https://marketplace-orchestrator.com",
                    "refresh_token": refresh_token,
                },
            )
            .json()
            .get("access_token")
        )
    return access_token

def create_target(access_token, target):
    # Create a new test target
    url = f"https://api.sandbox.mindgard.ai/api/v1/targets"
    response = requests.post(url=url, headers={"Authorization": f"Bearer {access_token}"}, json=target)
    target_id = response.json()['orchestrator_id']

    return target_id

def start_test(target_id, base_uri, access_token):
    # Start a test job for the new target
    create_job_uri = "/tests/jobs"
    create_job_request = {
        "target_id": target_id,
        "dataset_domain": "default",
        "duration": "sandbox"
    }
    response = requests.post(url=base_uri + create_job_uri, headers={"Authorization": f"Bearer {access_token}"}, json=create_job_request)
    job_id = response.json()['job']['orchestrator_id']

    # Wait for test job to finish
    status = None
    while status != "FINISHED":
        response = requests.get(url=base_uri + create_job_uri + "/" + target_id, headers={"Authorization": f"Bearer {access_token}"})
        status = response.json()[-1]["status"]
        print("Waiting for job to finish, current status is: " + status)
        time.sleep(10)
    return job_id

def fetch_tests_for_model(model_name: str, access_token: str) -> list[dict[str, Any]]:
    url = f"https://api.sandbox.mindgard.ai/api/v1/tests?model_name={model_name}"
    response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

    return [{"id": item["id"]} for item in response.json()["items"]]

def write_to_csv(model_name: str, attack_metadata: Any, compiled_responses: list[dict[str, Any]]):
    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow(["attack_id","target_name","submitted_at","answer", "prompt", "question", "classification"])

    for item in compiled_responses:
        csv_writer.writerow([
            attack_metadata.get("id", None),
            model_name,
            attack_metadata.get("submitted_at", None),
            item.get("prompt", None),
            item.get("answer", None),
            item.get("question", None),
            item.get("success") if item.get("flagged") is None else item.get("flagged")
            ])

def fetch_all_attacks_for_each_test(tests_by_model_name: list[dict[str, Any]], access_token: str):
    for test in tests_by_model_name:
        url = f"https://api.sandbox.mindgard.ai/api/v1/tests/{test.get('id', None)}/attacks"
        response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

        attack_ids = [test["attack"]["id"] for test in response.json()["items"]]
        for attack_id in attack_ids:
            url = f"https://api.sandbox.mindgard.ai/api/v1/tests/{test.get('id', None)}/attacks/{attack_id}"
            response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

            attack_result = response.json().get("result", {}) or {}
            model_name = attack_result.get("model", {}).get("name", None)
            metadata = attack_result.get("meta", {}) or {}
            results = attack_result.get("results", {}) or {}
            compiled_responses = results.get("compiled_responses") or []


            write_to_csv(model_name=model_name, attack_metadata=metadata, compiled_responses=compiled_responses)

base_uri = "https://api.sandbox.mindgard.ai/api/v1"
access_token = authenticate()
target_id = create_target(access_token=access_token, target=target)
start_test(target_id=target_id, base_uri=base_uri, access_token=access_token)
result = fetch_tests_for_model(model_name=target_name, access_token=access_token)
fetch_all_attacks_for_each_test(tests_by_model_name=result, access_token=access_token)

