# Description: This script fetches OpenAI completions and costs data for a
# specific project and outputs it in the influxDB line protocol format.
# Author: @arash77 (GitHub), and @sanjaysrikakulam (GitHub)
# Requirements: Environment variable OPENAI_API_KEY_TELEGRAF must be set with a valid OpenAI API key.

import os
import datetime
import logging
import requests

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


API_KEY = os.getenv("OPENAI_API_KEY_TELEGRAF")
if not API_KEY:
    logger.warning("OPENAI_API_KEY_TELEGRAF environment variable not set")
HEADERS = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

START_TIME = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
START_TIME_TS = int(START_TIME.timestamp())

PROJECT_IDS = ["proj_Al7GiZF7rlVHDMV8agVoppWi"]


def fetch_paginated_data(url, params):
    """Fetch paginated data from the OpenAI API."""
    results = []
    while True:
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            results.extend(data.get("data", []))
            if not data.get("has_more"):
                break
            params["page"] = data.get("next_page")
        except requests.RequestException as e:
            logger.error(f"Error fetching data from {url}: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
    return results


def process_completions():
    """Fetch OpenAI completions metrics and format it for InfluxDB."""
    url = "https://api.openai.com/v1/organization/usage/completions"
    params = {
        "start_time": START_TIME_TS,
        "limit": 31,
        "project_ids": PROJECT_IDS,
    }
    lines = []
    for bucket in fetch_paginated_data(url, params):
        try:
            timestamp = int(bucket["start_time"]) * 1_000_000_000
            result = (bucket.get("results") or [{}])[0]
            data = f"total_tokens={result.get('input_tokens', 0) + result.get('output_tokens', 0)},requests={result.get('num_model_requests', 0)}"
            lines.append(f"openai_completions {data} {timestamp}")
        except Exception as e:
            logger.error(f"Error processing completions bucket: {e}")
    return lines


def process_costs():
    """Fetch OpenAI cost metrics and format it for InfluxDB."""
    url = "https://api.openai.com/v1/organization/costs"
    params = {
        "start_time": START_TIME_TS,
        "limit": 180,
        "project_ids": PROJECT_IDS,
    }
    lines = []
    for bucket in fetch_paginated_data(url, params):
        try:
            timestamp = int(bucket["start_time"]) * 1_000_000_000
            cost = (bucket.get("results") or [{}])[0].get("amount", {}).get("value", 0.0)
            lines.append(f"openai_costs amount={cost:.4f} {timestamp}")
        except Exception as e:
            logger.error(f"Error processing costs bucket: {e}")
    return lines


if __name__ == "__main__":
    completions = process_completions()
    costs = process_costs()
    print("\n".join(completions + costs), flush=True)
