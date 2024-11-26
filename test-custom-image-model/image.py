import logging
import os
import random
from typing import List

import requests

from mindgard.test import Test, TestConfig, ImageModelConfig
from mindgard.wrappers.image import ImageModelWrapper, LabelConfidence

logging.basicConfig(format='%(asctime)s [%(levelname)-8s] %(name)s: %(message)s', level=logging.DEBUG)

# Get token for Mindgard API.
# Assumes you have previously run the CLI once on this machine and logged in, generating a ~/.mindgard/token.txt
config_folder = os.path.join(os.path.expanduser('~'), '.mindgard')
with open(os.path.join(config_folder, "token.txt"), "r") as f:
   refresh_token = f.read().strip()
   mindgard_access_token = (
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

# Override implementation of our Image Model Wrapper so that instead of calling an API run some custom code
class ExampleStubImageModelWrapper(ImageModelWrapper):
   def __init__(self, labels: List[str]) -> None:
       super().__init__(url="", labels=labels)

   # Example returning random scores for provided labels
   def __call__(self, image: bytes) -> List[LabelConfidence]:
       return [LabelConfidence(label=l,score=random.uniform(0, 1)) for l in self.labels]

image_wrapper = ExampleStubImageModelWrapper(labels=["0","1","2"])

config = TestConfig(
   api_base="https://api.sandbox.mindgard.ai/api/v1",
   api_access_token=mindgard_access_token,
   target="my-image-model",
   attack_source="user",
   model=ImageModelConfig(
       labels = image_wrapper.labels,
       wrapper=image_wrapper,
       dataset="mnist"
   ),
   parallelism=5
)

test = Test(config)
test.run()
