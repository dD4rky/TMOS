from tinkoff.invest import MoneyValue, Quotation
import math

def obj_to_scalar(value: MoneyValue | Quotation):
    return value.units + value.nano / 1_000_000_000

def scalar_to_quotation(value : float):
    return Quotation(units = math.floor(value), nano = round((value - math.floor(value)) * 1_000_000_000))
