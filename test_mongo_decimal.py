import bson.decimal128
import decimal
d = bson.decimal128.Decimal128("2.00")
print(d.to_decimal())
