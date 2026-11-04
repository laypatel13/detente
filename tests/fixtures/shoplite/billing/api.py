from billing.invoices import Invoice, total_due


def bill_user(user, amount):
    return Invoice(user, amount)


def balance(invoices):
    return {"due": total_due(invoices)}
