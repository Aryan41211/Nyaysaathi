"""
Compatibility module expected by some older code/tests.

If other contracts expect these helpers, re-export safe JSON envelopes
that match current API behavior patterns.
"""

from typing import Any, Dict


def success_response(data: Any = None, message: str = "Success", **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return payload


def error_response(code: str = "error", message: str = "Error", **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": False, "code": code, "message": message}
    payload.update(extra)
    return payload
