from type import Header
import json


def get_headers() -> Header:
    with open("headers.json", "r") as f:
        return json.load(f)
