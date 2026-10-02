from typing import Annotated

from fastapi import APIRouter, Header, Request

from api.v2 import Identity
from backend.models.contracts_v2 import UploadRequestV2
from backend.services.uploads_v2 import complete_upload, init_upload, resume_upload, write_part

router = APIRouter(prefix="/api/v2/uploads", tags=["V2 uploads"])


@router.post("", status_code=201)
def create(request: UploadRequestV2, actor: Identity):
    return init_upload(request, actor)


@router.get("/{upload_id}")
def resume(upload_id: str, actor: Identity):
    return resume_upload(upload_id, actor)


@router.put("/{upload_id}/parts/{number}")
async def part(upload_id: str, number: int, request: Request, actor: Identity, x_part_sha256: Annotated[str, Header()]):
    return await write_part(upload_id, number, x_part_sha256, request.stream(), actor)


@router.post("/{upload_id}/complete")
def complete(upload_id: str, actor: Identity):
    return complete_upload(upload_id, actor)
