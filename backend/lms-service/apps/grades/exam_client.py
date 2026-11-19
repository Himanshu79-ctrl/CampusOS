"""
Exam Engine Integration Boundary for CampusOS LMS.
Provides a decoupled interface to the Exam Engine microservice (SRS Section 3.F).
Handles external exam result fetching and status reporting without blocking independent LMS Gradebook workflows.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ExamEngineClient:
    """
    Decoupled client interface for retrieving exam scores from the external Exam Engine microservice.
    """

    @classmethod
    def get_service_url(cls) -> str:
        return getattr(settings, "EXAM_ENGINE_SERVICE_URL", "").rstrip("/")

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.get_service_url())

    @classmethod
    def fetch_exam_results(cls, external_exam_id: str, course_offering_id: int = None) -> dict:
        """
        Retrieves exam scores from the Exam Engine service.
        If the Exam Engine service is not configured or not running,
        returns an explicit status dictionary without throwing uncaught errors.
        """
        if not external_exam_id:
            return {
                "status": "ERROR",
                "message": "No external_exam_id provided.",
                "results": [],
            }

        service_url = cls.get_service_url()
        if not service_url:
            return {
                "status": "PENDING_INTEGRATION",
                "message": (
                    "Exam Engine service integration endpoint (EXAM_ENGINE_SERVICE_URL) is not yet configured. "
                    "Exam scoring is being developed by the Exam Engine team."
                ),
                "external_exam_id": external_exam_id,
                "results": [],
            }

        # If configured, make HTTP request
        try:
            import urllib.request
            import json

            url = f"{service_url}/api/exams/{external_exam_id}/results"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "status": "SUCCESS",
                    "external_exam_id": external_exam_id,
                    "results": data.get("results", data if isinstance(data, list) else []),
                }
        except Exception as exc:
            logger.warning(f"Exam Engine request failed for exam {external_exam_id}: {exc}")
            return {
                "status": "UNAVAILABLE",
                "message": f"Could not reach Exam Engine service at {service_url}: {str(exc)}",
                "external_exam_id": external_exam_id,
                "results": [],
            }

