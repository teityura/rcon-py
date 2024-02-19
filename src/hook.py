#!/usr/bin/env python3
import argparse
import json
import os

import requests
from dotenv import load_dotenv

SRC_DIR = os.path.dirname(__file__)
load_dotenv(f"{SRC_DIR}/config/.env")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def send_command(command, args):
    content = f"/{command} {' '.join(args)}"
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": content})

    if response.headers["content-type"] == "application/json":
        print(json.dumps(response.json(), indent=4))
    else:
        print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a command via Discord webhook.")
    parser.add_argument("command", type=str, help="The command to send.")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="The arguments to the command.")

    args = parser.parse_args()

    send_command(args.command, args.args)
