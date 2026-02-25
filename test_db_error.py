import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.execution_engine.models import Trade

try:
    print(Trade.objects.filter(realized_pnl__gt=0).count())
except Exception as e:
    import traceback
    traceback.print_exc()
