from cart.totals import cart_total


def add_item(lines, price, quantity=1):
    return [*lines, (price, quantity)]


def checkout(lines):
    return {"total": cart_total(lines)}
