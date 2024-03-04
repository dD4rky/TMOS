from tinkoff.invest import MoneyValue, Quotation

def obj_to_scalar(value: MoneyValue | Quotation):
    return value.units + value.nano / 1_000_000_000

def scalar_to_quotation(value : float):
    return Quotation(units = int(value), nano = int((value - int(value)) * 1_000_000_000))
