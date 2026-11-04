def line_total(price, quantity):
    return price * quantity


def cart_total(lines):
    return sum(line_total(price, quantity) for price, quantity in lines)
