from django.contrib import admin
from .models import OHLCVBar


@admin.register(OHLCVBar)
class OHLCVBarAdmin(admin.ModelAdmin):
    list_display = ["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
    list_filter = ["timeframe", "source"]
    search_fields = ["symbol"]
    ordering = ["-timestamp"]
