import json

from fastapi import FastAPI

app = FastAPI()


def read_json(file_name):
    with open(f"data/{file_name}", "r") as file:
        return json.load(file)


@app.get("/")
def home():
    return {"message": "Ford V&V Mock Toolchain API"}


@app.get("/jama/requirements")
def get_requirements():
    return read_json("requirements.json")


@app.get("/testrail/tests")
def get_tests():
    return read_json("tests.json")


@app.get("/jira/defects")
def get_defects():
    return read_json("defects.json")