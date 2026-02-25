from django.apps import AppConfig


class BrokerConnectorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.broker_connector"
    verbose_name = "Broker Connector"
