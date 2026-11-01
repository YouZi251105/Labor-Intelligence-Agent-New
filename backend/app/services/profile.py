def mask_identity_number(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) == 15 and normalized.isdigit():
        return f"{normalized[:3]}{'*' * 8}{normalized[-4:]}"
    if (
        len(normalized) == 18
        and normalized[:17].isdigit()
        and (normalized[-1].isdigit() or normalized[-1] == "X")
    ):
        return f"{normalized[:3]}{'*' * 11}{normalized[-4:]}"
    return ""
