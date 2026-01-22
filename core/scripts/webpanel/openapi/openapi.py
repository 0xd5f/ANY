from fastapi import FastAPI

from config import CONFIGS


def setup_openapi_schema(app: FastAPI):

    app.openapi_schema = app.openapi()

    app.openapi_schema["servers"] = [
        {
            "url": f"/{CONFIGS.ROOT_PATH}",
            "description": "Root path of the API"
        }
    ]

    app.openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization"
        }
    }

    for path, operations in app.openapi_schema["paths"].items():
        if path.startswith("/api/v1/"):
            for operation in operations.values():
                if "security" not in operation:
                    operation["security"] = []
                operation["security"].append({"ApiKeyAuth": []})
