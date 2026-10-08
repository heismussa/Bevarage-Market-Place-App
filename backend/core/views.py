from django.http import JsonResponse
from django.views import defaults

from core.errors import ErrorCode, error_payload


def _is_api(request):
    return request.path.startswith("/api/")


def not_found(request, exception=None):
    if _is_api(request):
        return JsonResponse(error_payload(ErrorCode.NOT_FOUND, "Not found."), status=404)
    return defaults.page_not_found(request, exception)


def server_error(request):
    if _is_api(request):
        return JsonResponse(
            error_payload(ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."),
            status=500,
        )
    return defaults.server_error(request)
