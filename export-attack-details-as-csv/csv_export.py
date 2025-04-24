import dataclasses
from typing import Any

import requests
import os
import sys
import csv

# Authenticate
def authenticate() -> str:
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

@dataclasses.dataclass
class TestApiResponse:
    id: str
    created_at: str
    # source: str
    mindgard_model_name: str
    # has_finished: bool
    # is_owned: bool
    # total_events: int
    # flagged_events: int
    # attacks:
    # model_type: str

# Fetch tests by model_name
def fetch_tests_for_model(model_name: str, access_token: str) -> list[dict[str, Any]]:
    url = f"https://api.sandbox.mindgard.ai/api/v1/tests?model_name={model_name}"
    response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

    return [{"id": item["id"]} for item in response.json()["items"]]

def write_to_csv(model_name: str, attack_metadata: Any, compiled_responses: list[dict[str, Any]]):
    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow(["attack_id","target_name","submitted_at","answer", "prompt", "question", "classification"])

    for item in compiled_responses:
        csv_writer.writerow([
            attack_metadata["id"],
            model_name,
            attack_metadata["submitted_at"],
            item["prompt"],
            item["answer"],
            item["question"],
            item["success"] if item["flagged"] is None else item["flagged"]
            ])

def fetch_all_attacks_for_each_test(tests_by_model_name: list[dict[str, Any]], access_token: str):
    for test in tests_by_model_name:
        url = f"https://api.sandbox.mindgard.ai/api/v1/tests/{test["id"]}/attacks"
        response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

        attack_ids = [test["attack"]["id"] for test in response.json()["items"]]
        for attack_id in attack_ids:
            url = f"https://api.sandbox.mindgard.ai/api/v1/tests/{test["id"]}/attacks/{attack_id}"
            response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

            attack_result = response.json()["result"]
            model_name = attack_result["model"]["name"]
            metadata = attack_result["meta"]
            compiled_responses = attack_result["results"]["compiled_responses"]

            write_to_csv(model_name=model_name, attack_metadata=metadata, compiled_responses=compiled_responses)





access_token = authenticate()
result = fetch_tests_for_model(model_name="openai-using-preset", access_token=access_token)
fetch_all_attacks_for_each_test(tests_by_model_name=result, access_token=access_token)