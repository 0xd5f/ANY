from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
import json
from ..schema.config.extra_config import (
    AddExtraConfigBody,
    EditExtraConfigBody,
    DeleteExtraConfigBody,
    ExtraConfigListResponse,
)
import cli_api

router = APIRouter()

@router.get('/list', response_model=ExtraConfigListResponse, summary='Get All Extra Configs')
async def get_all_extra_configs():
    try:
        configs_str = cli_api.list_extra_configs()
        if not configs_str:
            return []
        return json.loads(configs_str)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse extra configs list: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve extra configs: {str(e)}")


@router.post('/add', response_model=DetailResponse, summary='Add Extra Config')
async def add_extra_config(body: AddExtraConfigBody):
    try:
        cli_api.add_extra_config(body.name, body.uri)
        return DetailResponse(detail=f"Extra config '{body.name}' added successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/edit', response_model=DetailResponse, summary='Edit Extra Config')
async def edit_extra_config(body: EditExtraConfigBody):
    try:
        cli_api.edit_extra_config(body.name, body.new_name, body.uri, body.enabled)
        return DetailResponse(detail=f"Extra config '{body.new_name or body.name}' updated successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/delete', response_model=DetailResponse, summary='Delete Extra Config')
async def delete_extra_config(body: DeleteExtraConfigBody):
    try:
        cli_api.delete_extra_config(body.name)
        return DetailResponse(detail=f"Extra config '{body.name}' deleted successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))