#!/usr/bin/env python3
"""
Test script to check EVM API endpoint
"""

import requests

# Test the EVM timeseries endpoint
url = "http://localhost:8020/api/v1/evm/project/a8867141-f231-43eb-8ab5-062afd4ba147/timeseries"
params = {"granularity": "week", "branch": "main", "branch_mode": "merge"}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("✅ EVM API endpoint is working!")
    else:
        print("❌ EVM API endpoint failed")

except requests.exceptions.RequestException as e:
    print(f"❌ Failed to connect: {e}")
