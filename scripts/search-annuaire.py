#!/usr/bin/env python3
import os
import sys
import requests

session = requests.Session()
session.headers.update({
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.environ["ALBERT_OPENAI_API_KEY"]}'
})

response = session.post(
    'https://albert.api.etalab.gouv.fr/v1/search',
    json={
        'collections': [783],         # Annuaire des administrations d'état
        'rff_k': 20,                  # for now I don't know what this is
        'k': 3,                       # Top K
        'method': 'semantic',         # for now I don't know the functional consequences
        'score_threshold': 0.35,      # for now I don't know what this is
        'web_search': False,
        'prompt': sys.argv[1],
        'additionalProp1': {}
    }
)
if response.status_code == 200:
    print(response.text)
else:
    print("error", response.status_code)
