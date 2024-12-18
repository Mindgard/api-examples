import time
import requests
import os
import sys
import csv

# Creates a target, runs a test, prints results
# Usage: $ python create_and_test_target.py

api_key = "***REPLACE_WITH_API_KEY_FOR_TARGET_UNDER_TEST***"
target_name = "example-target-1"
url = "https://example-endpoint.aws.endpoints.huggingface.cloud.example.com"

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

base_uri = "https://api.sandbox.mindgard.ai/api/v1"

# Create a new test target
create_target_uri = "/targets"
target = {
    "model_type": "llm",
    "dataset": "Bad Questions",
    "target": target_name,
    "preset": "huggingface",
    "url": url,
    "api_key": api_key,
    "headers": "Authorization: Bearer " + api_key,
    "selector": "$[*].generated_text",
    "request_template": "{\"inputs\": \"[INST] {system_prompt} {prompt} [/INST]\", \"parameters\": {\"temperature\": 0.001}}",
    "system_prompt": "Please answer the question: "
}
response = requests.post(url=base_uri + create_target_uri, headers={"Authorization": f"Bearer {access_token}"}, json=target)
target_id = response.json()['orchestrator_id']
print("Created target with id " + target_id )

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

# Print out the results of the test
stats_uri = f"/results?model_name={target_name}"
response = requests.get(url=base_uri + stats_uri, headers={"Authorization": f"Bearer {access_token}"})

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