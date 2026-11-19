"""
Core system views for CampusOS LMS service.
"""

import logging
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def check_database_connection():
    """
    Executes a lightweight query to verify direct database connectivity.
    Raises an exception if the database is unreachable.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchone()


class HealthCheckView(APIView):
    """
    Health check endpoint verifying application and database connectivity.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            check_database_connection()
            db_status = "connected"
            http_status = status.HTTP_200_OK
            response_status = "ok"
        except Exception as exc:
            # Log error securely on server without exposing credentials or internal traces to client
            logger.error("Health check database probe failed: %s", exc.__class__.__name__)
            db_status = "disconnected"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            response_status = "error"

        return Response(
            {
                "status": response_status,
                "service": "CampusOS LMS",
                "database": db_status,
            },
            status=http_status,
        )
