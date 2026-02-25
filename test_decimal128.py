import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.dashboard.models import Strategy

if not Strategy.objects.exists():
    Strategy.objects.create(name="Test Strategy")

try:
    s = Strategy.objects.first()
    print("Value:", s.position_size_pct)
    print("Type:", type(s.position_size_pct))
    s.save()
    print("Saved successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
