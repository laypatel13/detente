from dataclasses import dataclass


@dataclass
class Invoice:
    user: str
    amount: int


def total_due(invoices):
    return sum(invoice.amount for invoice in invoices)
