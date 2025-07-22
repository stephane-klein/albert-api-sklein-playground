#!/usr/bin/env python3
import os
import argparse
import requests


def main():
    parser = argparse.ArgumentParser(description='Upload Pipelines function on Open WebUI')
    parser.add_argument('path', 
                       help='Pipeline file path to upload')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: File '{args.path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(args.path):
        print(f"Error: '{args.path}' is not a file", file=sys.stderr)
        sys.exit(1)
    
    session = requests.Session()

    session.headers.update({"Authorization": f"Bearer {os.environ['OPEN_WEBUI_API_KEY_SECRET']}"})

    urlIdx = session.get(f"{os.environ['OPEN_WEBUI_BASE_URL']}/api/v1/pipelines/list").json()["data"][0]["idx"]

    with open(args.path, "r") as f:
        response = session.post(
            f"{os.environ['OPEN_WEBUI_BASE_URL']}/api/v1/pipelines/upload",
            files={
                "file": (os.path.basename(args.path), f, "text/x-python")
            },
            data={
                "urlIdx": urlIdx
            }
        )
        print(response.text)


if __name__ == "__main__":
    main()
