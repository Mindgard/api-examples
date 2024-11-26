import requests
import os
import logging
import json
import sys
import csv

# Generates a csv with full results of all tests for a given model/target
# Usage: $ python csvattacks.py > results.csv

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

# Replace with the name of the model or target you wish to pull results for
model_name = "gpt-4o-mini-2024-07-18"

# Query for summary results for all tests of this target
url = f"https://api.sandbox.mindgard.ai/api/v1/results?model_name={model_name}"
response = requests.get(url=url, headers={"Authorization": f"Bearer {access_token}"})

# Grab the IDs of all attack techniques run against this target
result_summary = response.json()["items"]
attack_ids = [result["id"] for result in result_summary]

# To write the results as CSV to stdout
csv_writer = csv.writer(sys.stdout)
# Header row
csv_writer.writerow(["attack_id","target_name","submitted_at","answer", "prompt", "question", "classification"])


for id in attack_ids:
    # Get the full results for each attack technique
    attack_details_url = f"https://api.sandbox.mindgard.ai/api/v1/results/{id}"
    attack_result = requests.get(url=attack_details_url, headers={"Authorization": f"Bearer {access_token}"}).json()

    # Write to stdout in CSV format
    if "results" in attack_result and "compiled_responses" in attack_result['results']:
        for sample in attack_result['results']['compiled_responses']:
            csv_writer.writerow([attack_result['meta']['id'],
                 attack_result['model']['name'],
                 attack_result['meta']['submitted_at'],
                 attack_result['results']['system_prompt'],
                 sample['answer'],
                 sample['prompt'],
                 sample['question'],
                 sample['success']
            ])
