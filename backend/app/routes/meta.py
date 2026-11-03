from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.meta import DictionaryResponse
from app.services.dictionary import dictionary_payload, get_active_package

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/dictionary", response_model=DictionaryResponse)
async def get_dictionary(session: DbSession) -> DictionaryResponse:
    """返回纠纷类型、案件阶段、证据类别的统一字典（已发布包或内置默认）。"""
    package = await get_active_package(session)
    return DictionaryResponse.model_validate(dictionary_payload(package))
