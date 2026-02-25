import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.template.loader import get_template
try:
    get_template('dashboard/overview.html')
except Exception as e:
    import traceback
    traceback.print_exc()
