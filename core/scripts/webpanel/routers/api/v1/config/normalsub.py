from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
from ..schema.config.normalsub import (
    StartInputBody, EditSubPathInputBody, GetSubPathResponse, 
    EditProfileTitleInputBody, GetProfileTitleResponse,
    EditShowUsernameInputBody, GetShowUsernameResponse,
    EditSupportUrlInputBody, GetSupportUrlResponse
)
import cli_api

router = APIRouter()


@router.post('/start', response_model=DetailResponse, summary='Start NormalSub')
async def normal_sub_start_api(body: StartInputBody):
    try:

        cli_api.start_normalsub(body.domain, body.port)
        return DetailResponse(detail='Normalsub started successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.delete('/stop', response_model=DetailResponse, summary='Stop NormalSub')
async def normal_sub_stop_api():

    try:
        cli_api.stop_normalsub()
        return DetailResponse(detail='Normalsub stopped successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.put('/edit_subpath', response_model=DetailResponse, summary='Edit NormalSub Subpath')
async def normal_sub_edit_subpath_api(body: EditSubPathInputBody):
    try:
        cli_api.edit_normalsub_subpath(body.subpath)
        return DetailResponse(detail=f'Normalsub subpath updated to {body.subpath} successfully.')
    except cli_api.InvalidInputError as e:
        raise HTTPException(status_code=422, detail=f'Validation Error: {str(e)}')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/subpath', response_model=GetSubPathResponse, summary='Get Current NormalSub Subpath')
async def normal_sub_get_subpath_api():
    try:
        current_subpath = cli_api.get_normalsub_subpath()
        return GetSubPathResponse(subpath=current_subpath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving subpath: {str(e)}')

@router.put('/edit_profile_title', response_model=DetailResponse, summary='Edit NormalSub Profile Title')
async def normal_sub_edit_profile_title_api(body: EditProfileTitleInputBody):
    try:
        cli_api.edit_normalsub_profile_title(body.title)
        return DetailResponse(detail=f'Normalsub profile title updated to "{body.title}" successfully.')
    except cli_api.InvalidInputError as e:
        raise HTTPException(status_code=422, detail=f'Validation Error: {str(e)}')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/profile_title', response_model=GetProfileTitleResponse, summary='Get Current NormalSub Profile Title')
async def normal_sub_get_profile_title_api():
    try:
        current_title = cli_api.get_normalsub_profile_title()
        return GetProfileTitleResponse(title=current_title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving profile title: {str(e)}')

@router.put('/edit_support_url', response_model=DetailResponse, summary='Edit NormalSub Support URL')
async def normal_sub_edit_support_url_api(body: EditSupportUrlInputBody):
    try:
        cli_api.edit_normalsub_support_url(body.url)
        return DetailResponse(detail=f'Normalsub support URL updated successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/support_url', response_model=GetSupportUrlResponse, summary='Get Current NormalSub Support URL')
async def normal_sub_get_support_url_api():
    try:
        current_url = cli_api.get_normalsub_support_url()
        return GetSupportUrlResponse(url=current_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving support URL: {str(e)}')

@router.put('/edit_show_username', response_model=DetailResponse, summary='Edit NormalSub Show Username')
async def normal_sub_edit_show_username_api(body: EditShowUsernameInputBody):
    try:
        cli_api.edit_normalsub_show_username(body.enabled)
        status = "enabled" if body.enabled else "disabled"
        return DetailResponse(detail=f'Show Username setting {status} successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/show_username', response_model=GetShowUsernameResponse, summary='Get Current NormalSub Show Username')
async def normal_sub_get_show_username_api():
    try:
        enabled = cli_api.get_normalsub_show_username()
        return GetShowUsernameResponse(enabled=enabled)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving setting: {str(e)}')