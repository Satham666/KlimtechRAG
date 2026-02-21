import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import settings
from ..fs_tools import (
    FsLimits,
    FsSecurityError,
    glob_paths,
    grep_files,
    ls_dir,
    read_text_file,
)
from ..models import FsListRequest, FsGlobRequest, FsReadRequest, FsGrepRequest
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id

router = APIRouter(tags=["filesystem"])
logger = logging.getLogger("klimtechrag")


@router.post("/fs/list")
async def fs_list(
    request_body: FsListRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        return ls_dir(settings.fs_root, request_body.path)
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error executing ls: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail="ls execution failed")


@router.post("/fs/glob")
async def fs_glob(
    request_body: FsGlobRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        return glob_paths(
            settings.fs_root, request_body.pattern, limit=request_body.limit
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "Error executing glob: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail="glob failed")


@router.post("/fs/read")
async def fs_read(
    request_body: FsReadRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )
    try:
        return read_text_file(
            settings.fs_root,
            request_body.path,
            limits=limits,
            offset=request_body.offset,
            limit=request_body.limit,
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fs/grep")
async def fs_grep(
    request_body: FsGrepRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )
    try:
        return grep_files(
            settings.fs_root,
            request_body.path,
            request_body.query,
            limits=limits,
            file_glob=request_body.file_glob,
            regex=request_body.regex,
            case_insensitive=request_body.case_insensitive,
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
