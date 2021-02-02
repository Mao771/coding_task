import json
import uuid
import uvicorn

from typing import Optional

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


app = FastAPI()


class GeneralSettings(BaseModel):
    appVersion: str
    description: str


class Hyperparameters(BaseModel):
    bootstrap: bool
    criterion: str
    maxDepth: Optional[int]
    maxFeatures: str
    maxLeafNodes: Optional[int]
    minImpurityDecrease: float
    nEstimators: int
    nJobs: int


class OptimizationTask(BaseModel):
    generalSettings: GeneralSettings
    hyperparameters: Hyperparameters


def serialize_optimization_task(optimization_task: OptimizationTask):
    result = optimization_task.generalSettings.dict()
    hyperparameters = []
    for key, value in optimization_task.hyperparameters.dict().items():
        hyperparameters.append(key)
        hyperparameters.append(str(value))
    result['hyperparamters'] = hyperparameters

    return result


def read_from_cache():
    try:
        with open('request_cache.json') as f:
            try:
                request_cache = json.load(f)
            except ValueError:
                request_cache = {}
    except FileNotFoundError:
        request_cache = {}

    return request_cache


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse({"message": 'Not all mandatory fields are filled.'}, status_code=401)


@app.post("/api/optimization/task")
async def create_optimization_task(optimization_task: OptimizationTask):
    optimization_task_serialized = serialize_optimization_task(optimization_task)
    request_cache = read_from_cache()

    for task in request_cache.values():
        if task == optimization_task_serialized:
            return JSONResponse({"message": 'Duplicate request'}, status_code=409)

    task_id = str(uuid.uuid4())
    request_cache[task_id] = optimization_task_serialized

    with open('request_cache.json', 'w+') as f:
        json.dump(request_cache, f)

    return {"id": task_id}


@app.get("/api/optimization/task/{task_id}")
async def get_optimization_task(task_id: str):
    request_cache = read_from_cache()

    if task_id in request_cache:
        return {task_id: {"configuration": request_cache[task_id]}}
    else:
        return JSONResponse({"message": 'Task does not exist'}, status_code=404)


@app.get("/api/optimization/tasks")
async def get_optimization_task():
    request_cache = read_from_cache()
    response = {task_id: {"configuration": task} for task_id, task in request_cache.items()}

    return response

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0")
