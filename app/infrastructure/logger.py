import os
import json
import uuid
import time
import requests
import logging

from datetime import datetime, timezone
from typing import Any, Optional, Dict
from dotenv import load_dotenv


load_dotenv()
terminal_logger = logging.getLogger("uvicorn.error")


class Logging:
    def __init__(self,agent_name: str,source_module: str,timeout: int = 10,) -> None:

        self.base_url = os.getenv("LOG_URL")

        if not self.base_url:
            raise ValueError(
                "LOG_URL is not set in environment variables."
            )

        self.agent_name = agent_name
        self.source_module = source_module
        self.timeout = timeout

    def log(
        self,
        message: str,
        event_type: str,
        is_success: bool = True,
        duration_ms: int = 0,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None) -> None:

        log_payload = {
            "agentName": self.agent_name,
            "message": message,
            "eventType": event_type,
            "sourceModule": self.source_module,
            "isSuccess": is_success,
            "durationMs": duration_ms,
            "startTime": start_time,
            "endTime": end_time,
            "payloadJson": json.dumps(
                payload or {},
                default=str,
            ),
            "correlationId": (
                correlation_id or str(uuid.uuid4())
            ),
        }

        terminal_logger.info(
            "[EnterpriseLogger] submission started | event=%s | correlation_id=%s",
            event_type,
            log_payload["correlationId"],
        )
        try:
            response = requests.post(
                self.base_url,
                json=log_payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            terminal_logger.info(
                "[EnterpriseLogger] submitted successfully | event=%s | status=%s | correlation_id=%s",
                event_type,
                response.status_code,
                log_payload["correlationId"],
            )

        except requests.RequestException as exc:
            terminal_logger.warning(
                "[EnterpriseLogger] submission failed | event=%s | correlation_id=%s | error=%s",
                event_type,
                log_payload["correlationId"],
                exc,
            )

    def start(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start tracking an operation.

        Returns a tracking token that must be passed to end().
        """

        token = {
            "message": message,
            "event_type": event_type,
            "correlation_id": (
                correlation_id or str(uuid.uuid4())
            ),
            "start_perf": time.perf_counter(),
            "start_time": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        terminal_logger.info(
            "[EnterpriseLogger] tracking started | event=%s | correlation_id=%s",
            event_type,
            token["correlation_id"],
        )
        return token

    def end(
        self,
        tracking_token: Dict[str, Any],
        is_success: bool = True,
        payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> None:
        """
        Finish tracking and send the enterprise log.
        """

        end_perf = time.perf_counter()
        end_time = datetime.now(timezone.utc).isoformat()

        duration_ms = round(
            (
                end_perf
                - tracking_token["start_perf"]
            )
            * 1000
        )

        self.log(
            message=message or tracking_token["message"],
            event_type=(
                event_type
                or tracking_token["event_type"]
            ),
            is_success=is_success,
            duration_ms=duration_ms,
            start_time=tracking_token["start_time"],
            end_time=end_time,
            payload=payload,
            correlation_id=tracking_token[
                "correlation_id"
            ],
        )



# ==========================================================
# Usage
# ==========================================================

# # 1. Import the logger
# # from app.infrastructure.logger import Logging

# # 2. Create a logger instance
# logger = Logging(
#     agent_name="Your Agent Name ",
#     source_module="like you api router or node",
# )

# # 3. Start tracking an operation
# tracking_token = logger.start(
#     message=" 'Your Agent name' generation started",
#     event_type="'Your Task Name'GenerationStarted",
# )

# try:
#     # =================================
#     # Your Code comes  logic
#     # ===========================
#     response = "llm"

#     # 4. End tracking (Success)
#     logger.end(
#         tracking_token=tracking_token,
#         is_success=True,
#         message="Win theme generation completed",
#         event_type="WinThemeGenerationCompleted",
#         payload={
#             "company_id": "12345",
#             "generated_themes": 5,
#         },
#     )

# except Exception as exc:

#     # 5. End tracking (Failure)
#     logger.end(
#         tracking_token=tracking_token,
#         is_success=False,
#         message="Win theme generation failed",
#         event_type="WinThemeGenerationFailed",
#         payload={
#             "error": str(exc),
#         },
#     )

#     raise
