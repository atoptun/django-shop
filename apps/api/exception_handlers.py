import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that logs unhandled exceptions
    and returns a standardized JSON response.
    """
    response = exception_handler(exc, context)

    if response is None:
        logger.error(f"Unhandled Exception: {exc}", exc_info=True)

        custom_response_data = {
            "error": "Internal Server Error",
            "message": "Somthing went wrong. Please try again later.",
            "details": str(exc) if settings.DEBUG else None,
        }

        return Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
