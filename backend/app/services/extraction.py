from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from shutil import which
from typing import Literal, Protocol

from docx import Document as DocxDocument
from pypdf import PdfReader

ExtractionStatus = Literal["extracted", "ocr_required", "unsupported", "failed"]

MAX_EXTRACTED_CHARS = 200_000
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", *IMAGE_EXTENSIONS}


@dataclass(frozen=True)
class ExtractionResult:
    status: ExtractionStatus
    text: str
    message: str
    provider: str

    def as_assessment(self) -> dict[str, str | int]:
        data = asdict(self)
        data.pop("text")
        data["text_length"] = len(self.text)
        return data


class OCRProvider(Protocol):
    name: str

    def extract(self, filename: str, content: bytes) -> ExtractionResult: ...


class TesseractOCRProvider:
    name = "tesseract"

    def extract(self, filename: str, content: bytes) -> ExtractionResult:
        if which("tesseract") is None:
            return ExtractionResult(
                status="ocr_required",
                text="",
                message="当前环境未配置 OCR 引擎，图片已保存，请配置 OCR 后重试。",
                provider=self.name,
            )
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return ExtractionResult(
                status="ocr_required",
                text="",
                message="当前环境未安装图片 OCR 组件，图片已保存，请配置 OCR 后重试。",
                provider=self.name,
            )

        try:
            image = Image.open(BytesIO(content))
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        except Exception:
            return ExtractionResult(
                status="failed",
                text="",
                message="图片 OCR 识别失败，请检查图片是否完整或人工录入。",
                provider=self.name,
            )
        return _result_from_text(text, self.name)


DEFAULT_OCR_PROVIDER: OCRProvider = TesseractOCRProvider()


def extract_text_from_bytes(
    filename: str,
    content: bytes,
    content_type: str = "",
    ocr_provider: OCRProvider | None = None,
) -> ExtractionResult:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return ExtractionResult(
            status="unsupported",
            text="",
            message="当前仅支持 TXT、PDF、DOCX 和常见图片格式的文本提取。",
            provider="local",
        )

    if extension == ".txt":
        return _extract_txt(content)
    if extension == ".pdf":
        return _extract_pdf(content)
    if extension == ".docx":
        return _extract_docx(content)
    return (ocr_provider or DEFAULT_OCR_PROVIDER).extract(filename, content)


def _result_from_text(text: str, provider: str) -> ExtractionResult:
    normalized = _normalize_text(text)
    if not normalized:
        return ExtractionResult(
            status="ocr_required",
            text="",
            message="文件未提取到可复制文本，可能需要 OCR 或人工录入。",
            provider=provider,
        )
    return ExtractionResult(
        status="extracted",
        text=normalized,
        message=f"已提取 {len(normalized)} 个字符。",
        provider=provider,
    )


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.replace("\x00", "").splitlines()]
    normalized = "\n".join(line for line in lines if line)
    return normalized[:MAX_EXTRACTED_CHARS]


def _extract_txt(content: bytes) -> ExtractionResult:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return _result_from_text(content.decode(encoding), "local-text")
        except UnicodeDecodeError:
            continue
    return ExtractionResult(
        status="failed",
        text="",
        message="文本文件编码无法识别，请转换为 UTF-8 后重试。",
        provider="local-text",
    )


def _extract_pdf(content: bytes) -> ExtractionResult:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            return ExtractionResult(
                status="failed",
                text="",
                message="PDF 已加密，无法读取文本。",
                provider="pypdf",
            )
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ExtractionResult(
            status="failed",
            text="",
            message="PDF 文件损坏或无法解析。",
            provider="pypdf",
        )
    return _result_from_text(text, "pypdf")


def _extract_docx(content: bytes) -> ExtractionResult:
    try:
        document = DocxDocument(BytesIO(content))
        blocks = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                blocks.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(blocks)
    except Exception:
        return ExtractionResult(
            status="failed",
            text="",
            message="DOCX 文件损坏或无法解析。",
            provider="python-docx",
        )
    return _result_from_text(text, "python-docx")
