from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ApiSuccess:
    data: Any
    success: bool = True
    status: str = "success"


@dataclass(frozen=True)
class ApiError:
    error: str
    status: str = "error"
    success: bool = False


def success_envelope(payload: Dict[str, Any], *, data_key: str = "data") -> Dict[str, Any]:
    """
    Normalize responses to a stable JSON envelope.
    Keeps compatibility with existing tests that assert `success` exists.
    """
    if not isinstance(payload, dict):
        return {"success": True, "status": "success", "data": payload}

    payload = dict(payload)
    payload.setdefault("success", True)
    payload.setdefault("status", "success")
    payload.setdefault(data_key, payload.get(data_key))
    return payload


def error_envelope(message: str, *, code: str = "error") -> Dict[str, Any]:
    return {"success": False, "status": code, "error": message}
