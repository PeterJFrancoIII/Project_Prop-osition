from django.contrib import admin
from .models import BrokerAccount


@admin.register(BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ["account_id", "broker_type", "display_name", "mode", "status", "equity", "last_synced_at"]
    list_filter = ["broker_type", "mode", "status"]
    search_fields = ["account_id", "display_name"]
    readonly_fields = ["account_id", "created_at", "updated_at"]
    exclude = ["encrypted_api_key", "encrypted_secret_key"]  # Never show encrypted keys in admin
