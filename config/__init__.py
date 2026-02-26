# Apply Monkey Patch for Djongo/MongoDB Decimal128 type support
from django.db.models import DecimalField

original_to_python = DecimalField.to_python

def custom_to_python(self, value):
    # PyMongo returns BSON Decimal128 objects which crash Django's native DecimalField.to_python
    if hasattr(value, 'to_decimal'):
        value = value.to_decimal()
    return original_to_python(self, value)

def custom_from_db_value(self, value, expression, connection):
    if hasattr(value, 'to_decimal'):
        return value.to_decimal()
    return value

original_get_db_prep_value = DecimalField.get_db_prep_value
def custom_get_db_prep_value(self, value, connection, prepared=False):
    import bson.decimal128
    from decimal import Decimal
    val = original_get_db_prep_value(self, value, connection, prepared)
    if val is not None and isinstance(val, Decimal):
        return bson.decimal128.Decimal128(str(val))
    return val

DecimalField.to_python = custom_to_python
DecimalField.from_db_value = custom_from_db_value
DecimalField.get_db_prep_value = custom_get_db_prep_value

# Import Celery app on startup
from .celery import app as celery_app

__all__ = ('celery_app',)
