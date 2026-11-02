from fastapi import APIRouter

from app.schemas.meta import DictionaryResponse
from app.services.dictionary import dictionary_payload

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/dictionary", response_model=DictionaryResponse)
async def get_dictionary() -> DictionaryResponse:
    """返回纠纷类型、案件阶段、证据类别的统一字典。"""
    return DictionaryResponse.model_validate(dictionary_payload())
