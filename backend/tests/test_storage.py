from pathlib import Path

import pytest

from app.services.storage import LocalStorage


def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    key = storage.save("case-1/example.txt", "工资记录".encode())

    assert key == "case-1/example.txt"
    assert storage.exists(key)
    assert storage.read(key) == "工资记录".encode()

    storage.delete(key)
    assert not storage.exists(key)


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.save("../outside.txt", b"unsafe")
    with pytest.raises(ValueError):
        storage.read("case-1/../../outside.txt")
