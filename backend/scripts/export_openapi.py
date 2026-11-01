import json
from pathlib import Path

from app.main import app

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "docs" / "api" / "openapi.v1.json"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI exported to {OUTPUT_PATH.relative_to(ROOT_DIR).as_posix()}")


if __name__ == "__main__":
    main()
