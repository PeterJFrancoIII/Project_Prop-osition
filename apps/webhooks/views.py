"""
Webhook receiver views.

Receives TradingView POST webhooks, validates them, and dispatches
validated signals to the execution engine.
"""

import logging
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WebhookEvent
from .serializers import TradingViewWebhookSerializer
from apps.execution_engine.executor import execute_signal

logger = logging.getLogger(__name__)


class WebhookReceiveView(APIView):
    """
    POST /api/v1/webhooks/tradingview/

    Receives a TradingView webhook alert, validates the payload,
    logs it, and dispatches to the execution engine.
    """

    permission_classes = [AllowAny]  # Webhooks use token auth, not session/JWT
    throttle_scope = "webhook"

    def post(self, request):
        # --- Step 1: Authenticate via token ---
        auth_token = request.headers.get("X-API-Token", "")
        if auth_token != settings.WEBHOOK_AUTH_TOKEN:
            logger.warning("Webhook auth failed from %s", self._get_client_ip(request))
            return Response(
                {"status": "error", "data": None, "message": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # --- Step 2: Log raw event ---
        webhook_event = WebhookEvent.objects.create(
            source="tradingview",
            payload=request.data,
            ip_address=self._get_client_ip(request),
        )

        # --- Step 3: Validate payload ---
        serializer = TradingViewWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            webhook_event.status = "rejected"
            webhook_event.error_message = str(serializer.errors)
            webhook_event.save()
            logger.info("Webhook rejected: %s", serializer.errors)
            return Response(
                {"status": "error", "data": serializer.errors, "message": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data

        # --- Step 4: Update event with parsed data ---
        webhook_event.status = "validated"
        webhook_event.ticker = validated["ticker"]
        webhook_event.action = validated["action"]
        webhook_event.quantity = validated["quantity"]
        webhook_event.strategy = validated["strategy"]
        webhook_event.save()

        # --- Step 5: Dispatch to execution engine ---
        try:
            trades = execute_signal(validated)
            webhook_event.status = "dispatched"
            webhook_event.save()
            
            trade_ids = [t.trade_id for t in trades]
            logger.info(
                "Webhook dispatched → Trades %s | %s %s %s",
                trade_ids,
                validated["action"],
                validated["quantity"],
                validated["ticker"],
            )
            return Response(
                {
                    "status": "success",
                    "data": {
                        "webhook_id": webhook_event.webhook_id,
                        "trade_ids": trade_ids,
                        "symbol": validated["ticker"],
                        "side": validated["action"],
                        "quantity": validated["quantity"],
                    },
                    "message": f"Signal received and {len(trades)} trades executed",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            webhook_event.status = "error"
            webhook_event.error_message = str(e)
            webhook_event.save()
            logger.error("Webhook dispatch failed: %s", e, exc_info=True)
            return Response(
                {"status": "error", "data": None, "message": f"Execution failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_client_ip(self, request):
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
