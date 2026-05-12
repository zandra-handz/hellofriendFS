"""
Project-wide DRF error handling.

Two response shapes are produced depending on which surface the request hit:

  * Public mobile API -> {"detail": "human readable message"} for single errors,
    or DRF's field-keyed dict for serializer validation errors.
  * Internal Rust-facing endpoints (under /users/internal/) -> the
    {"action": ..., "data": {...}} shape the Rust socket already parses, so
    a Django-side failure doesn't show up as bad_django_response on Rust.

`error_response()` is the helper views should use when they explicitly want to
return a standardized error (validation failures, forbidden actions, etc.).
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


logger = logging.getLogger(__name__)


INTERNAL_PATH_PREFIXES = ("/users/internal/",)


def _is_internal_request(request) -> bool:
    if request is None:
        return False
    path = getattr(request, "path", "") or ""
    return any(path.startswith(p) for p in INTERNAL_PATH_PREFIXES)


def _internal_error_response(status_code: int) -> Response:
    return Response(
        {"action": "internal_error", "data": {"reason": "django_error"}},
        status=status_code,
    )


def _normalize_public_payload(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        first = data[0] if data else "Something went wrong"
        return {"detail": str(first)}
    return {"detail": str(data)}


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request") if context else None

    if response is None:
        logger.exception(
            "Unhandled exception in view %s", context.get("view") if context else None
        )
        if _is_internal_request(request):
            return _internal_error_response(status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(
            {"detail": "Something went wrong"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if _is_internal_request(request):
        return _internal_error_response(response.status_code)

    response.data = _normalize_public_payload(response.data)
    return response


def error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"detail": message}, status=status_code)
