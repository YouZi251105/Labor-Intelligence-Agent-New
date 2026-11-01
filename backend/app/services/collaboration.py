from fastapi import HTTPException

SERVICE_TRANSITIONS = {
    "pending": {"in_progress"},
    "in_progress": {"completed"},
    "completed": set(),
}

REVENUE_TRANSITIONS = {
    "pending": {"confirmed"},
    "confirmed": {"paid"},
    "paid": set(),
}


def validate_service_transition(current: str, target: str) -> None:
    if target not in SERVICE_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"服务记录不能从 {current} 变更为 {target}",
        )


def validate_revenue_transition(current: str, target: str) -> None:
    if target not in REVENUE_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"收益记录不能从 {current} 变更为 {target}",
        )
