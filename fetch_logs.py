import requests
import json
import os

token = "rnd_ddJcTu2n4gJCo380VdTrKGjYqIzM"
service_id = "srv-d8t4bb3tqb8s73dg3olg"
deploy_id = "dep-d8t4sp68bjmc73ea0g0g"

headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
print(f"Fetching logs for {deploy_id}...")
res = requests.get(f"https://api.render.com/v1/services/{service_id}/deploys/{deploy_id}", headers=headers)
print(json.dumps(res.json(), indent=2))
