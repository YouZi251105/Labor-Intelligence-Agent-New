import hashlib
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_DIR
from app.models.case import Case
from app.models.evidence import Evidence

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".doc", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024

DISPUTE_EVIDENCE = {
    "wage": ["payroll", "chat", "contract"],
    "termination": ["contract", "chat", "payroll"],
    "contract": ["contract", "chat", "attendance"],
    "overtime": ["attendance", "chat", "payroll"],
    "injury": ["medical", "chat", "contract"],
    "insurance": ["social_insurance", "payroll", "contract"],
    "service_pay": ["settlement", "chat", "payroll"],
    "general": ["contract", "chat", "payroll"],
}

CATEGORY_LABELS = {
    "contract": "合同或协议",
    "chat": "聊天记录",
    "payroll": "工资或转账记录",
    "attendance": "考勤或排班记录",
    "medical": "就医或伤情材料",
    "social_insurance": "社保记录",
    "settlement": "结算单",
    "other": "其他材料",
}


def detect_category(filename: str, content_type: str, text: str) -> str:
    value = f"{filename} {content_type} {text[:300]}".lower()
    if any(word in value for word in ["合同", "协议", "contract"]):
        return "contract"
    if any(word in value for word in ["聊天", "微信", "chat"]):
        return "chat"
    if any(word in value for word in ["工资", "流水", "转账", "payroll"]):
        return "payroll"
    if any(word in value for word in ["考勤", "排班", "attendance"]):
        return "attendance"
    if any(word in value for word in ["医院", "病历", "医疗", "medical"]):
        return "medical"
    if any(word in value for word in ["社保", "公积金", "insurance"]):
        return "social_insurance"
    if any(word in value for word in ["结算", "工程款", "settlement"]):
        return "settlement"
    return "other"


def validate_signature(extension: str, content: bytes) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if extension == ".pdf":
        return content.startswith(b"%PDF")
    if extension in {".docx", ".doc"}:
        return content.startswith(b"PK") or content.startswith(b"\xd0\xcf\x11\xe0")
    return extension == ".txt"


def save_upload(case_id: int, filename: str, content: bytes) -> tuple[Path, str]:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("不支持的文件类型")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件超过 20MB 限制")
    if not validate_signature(extension, content):
        raise ValueError("文件内容与扩展名不匹配")

    upload_dir = BACKEND_DIR / "data" / "uploads" / str(case_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    target = upload_dir / f"{digest[:16]}{extension}"
    target.write_bytes(content)
    return target, digest


def assess_case_evidence(case: Case, evidence_items: list[Evidence]) -> dict[str, Any]:
    required = DISPUTE_EVIDENCE.get(case.dispute_type, DISPUTE_EVIDENCE["general"])
    present = {item.category for item in evidence_items}
    missing = [category for category in required if category not in present]
    return {
        "status": "ready" if not missing else "needs_more",
        "required_categories": required,
        "present_categories": sorted(present),
        "missing_categories": missing,
        "missing_labels": [CATEGORY_LABELS[item] for item in missing],
        "message": (
            "当前材料已覆盖演示规则中的主要类别，可以进入文书草稿阶段。"
            if not missing
            else "当前材料仍有缺口，建议继续补充后再准备正式文书。"
        ),
        "disclaimer": "评估仅用于材料整理，不构成证据合法性或证明力结论。",
    }


def review_contract(text: str) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    checks = [
        ("自愿放弃社会保险", "high", "放弃社会保险条款", "该条款可能影响劳动者社会保险权益，应重点人工核验。"),
        ("随时解除", "high", "单方随时解除", "解除条件过于宽泛，可能增加被违法解除的风险。"),
        ("押金", "high", "收取押金", "用工方收取押金存在较高合规风险。"),
        ("违约金", "medium", "违约金条款", "需要确认违约金适用情形和金额是否合理。"),
        ("工资另行约定", "medium", "工资约定不明确", "工资标准不明确，容易引发欠薪和加班费争议。"),
    ]
    for keyword, level, title, detail in checks:
        if keyword in text:
            findings.append({"level": level, "title": title, "detail": detail})

    missing: list[str] = []
    if "工资" not in text:
        missing.append("工资标准和支付时间")
    if "工作时间" not in text and "工时" not in text:
        missing.append("工作时间和休息休假")
    if "解除" not in text:
        missing.append("合同解除条件")
    if "社会保险" not in text and "社保" not in text:
        missing.append("社会保险约定")

    risk_level = "high" if any(item["level"] == "high" for item in findings) else "medium"
    if not findings and len(missing) <= 1:
        risk_level = "low"
    if not findings:
        findings.append(
            {
                "level": "info",
                "title": "未命中演示规则中的明显风险关键词",
                "detail": "这不代表合同没有风险，仍需核对原件和完整条款。",
            }
        )

    return {
        "risk_level": risk_level,
        "findings": findings,
        "missing_items": missing,
        "disclaimer": "本结果仅基于粘贴文本进行规则提示，不构成合同真实性或法律效力结论。",
    }
