from django.urls import path
from .views import WebhookReceiveView

urlpatterns = [
    path("tradingview/", WebhookReceiveView.as_view(), name="webhook-tradingview"),
]
