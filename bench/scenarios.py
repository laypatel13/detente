"""Pairs of edits to the ShopLite fixture, one per laptop, with neither pushed.

`breaks` is the truth: True when these two changes really can't ship together.
An edit is (path, old text, new text). An empty old text creates the file.
`base` edits land in the shared commit before either laptop starts.
"""

from dataclasses import dataclass

from backend.plans import FlightPlan

Edit = tuple[str, str, str]

NEW_REFUND_CALLER = "from auth.session import create_session\n\n\ndef refund(user):\n    return create_session(user)\n"


@dataclass(frozen=True)
class Scenario:
    name: str
    breaks: bool
    plan_a: FlightPlan
    edits_a: tuple[Edit, ...]
    plan_b: FlightPlan
    edits_b: tuple[Edit, ...]
    base: tuple[Edit, ...] = ()


STORE = (
    "auth/store.py",
    "",
    "import secrets\n\n\nclass SessionStore:\n    def __init__(self):\n        self.sessions = {}\n\n"
    "    def open(self, user):\n        token = secrets.token_hex(16)\n        self.sessions[token] = user\n"
    "        return token\n\n    def close(self, token):\n        self.sessions.pop(token, None)\n\n"
    "    @classmethod\n    def empty(cls):\n        return cls()\n",
)
SETTINGS = (
    "config/settings.toml",
    "",
    '[session]\nttl = 3600\ncookie = "sid"\n\n[billing]\ncurrency = "USD"\n',
)
STORE_PLAN = FlightPlan("session ttl", ("auth/store.py",), changes=("auth.store.SessionStore.open",))
OPEN_NEEDS_TTL = (("auth/store.py", "def open(self, user):", "def open(self, user, ttl):"),)
RENAME_SESSION = (("auth/session.py", "def create_session(user):", "def open_session(user):"),)

SESSION_PLAN = FlightPlan(
    "session expiry", ("auth/session.py",), changes=("auth.session.create_session",)
)
REFUND_PLAN = FlightPlan(
    "refunds", ("billing/refunds.py",), uses=("auth.session.create_session",)
)
REFUND_EDIT = (("billing/refunds.py", "", NEW_REFUND_CALLER),)

SCENARIOS = (
    Scenario(
        "Both edit the same function",
        True,
        FlightPlan("rounding", ("cart/totals.py",), changes=("cart.totals.cart_total",)),
        (("cart/totals.py", "return sum(line_total(price, quantity) for price, quantity in lines)",
          "return round(sum(line_total(price, quantity) for price, quantity in lines), 2)"),),
        FlightPlan("discounts", ("cart/totals.py",), changes=("cart.totals.cart_total",)),
        (("cart/totals.py", "return sum(line_total(price, quantity) for price, quantity in lines)",
          "return max(0, sum(line_total(price, quantity) for price, quantity in lines))"),),
    ),
    Scenario(
        "Same file, different functions",
        False,
        FlightPlan("line tax", ("cart/totals.py",), changes=("cart.totals.line_total",)),
        (("cart/totals.py", "return price * quantity", "return round(price * quantity, 2)"),),
        FlightPlan("cart floor", ("cart/totals.py",), changes=("cart.totals.cart_total",)),
        (("cart/totals.py", "return sum(line_total(price, quantity) for price, quantity in lines)",
          "return max(0, sum(line_total(price, quantity) for price, quantity in lines))"),),
    ),
    Scenario(
        "New required parameter vs a new caller",
        True,
        SESSION_PLAN,
        (("auth/session.py", "def create_session(user):", "def create_session(user, ttl):"),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Function renamed vs a new caller",
        True,
        SESSION_PLAN,
        (("auth/session.py", "def create_session(user):", "def open_session(user):"),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Function deleted vs a new caller",
        True,
        SESSION_PLAN,
        (("auth/session.py",
          "def create_session(user):\n    token = secrets.token_hex(16)\n"
          "    SESSIONS[token] = user\n    return token\n\n\n", ""),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Keyword argument renamed",
        True,
        FlightPlan("naming", ("cart/items.py",), changes=("cart.items.add_item",)),
        (("cart/items.py", "def add_item(lines, price, quantity=1):\n    return [*lines, (price, quantity)]",
          "def add_item(lines, price, count=1):\n    return [*lines, (price, count)]"),),
        FlightPlan("bulk add", ("cart/bulk.py",), uses=("cart.items.add_item",)),
        (("cart/bulk.py", "",
          "from cart.items import add_item\n\n\ndef add_pair(lines, price):\n    return add_item(lines, price, quantity=2)\n"),),
    ),
    Scenario(
        "Class constructor gains a parameter",
        True,
        FlightPlan("currency", ("billing/invoices.py",), changes=("billing.invoices.Invoice",)),
        (("billing/invoices.py", "    amount: int\n", "    amount: int\n    currency: str\n"),),
        FlightPlan("credits", ("billing/credits.py",), uses=("billing.invoices.Invoice",)),
        (("billing/credits.py", "",
          "from billing.invoices import Invoice\n\n\ndef credit(user):\n    return Invoice(user, -10)\n"),),
    ),
    Scenario(
        "Two plans add the same endpoint",
        True,
        FlightPlan("refund endpoint", ("billing/api.py",), changes=("POST /refunds",)),
        (("billing/api.py", "def balance(invoices):", "def refund_endpoint(user):\n    return bill_user(user, -1)\n\n\ndef balance(invoices):"),),
        FlightPlan("refund route", ("billing/routes.py",), changes=("POST /refunds",)),
        (("billing/routes.py", "", "def refund_route(user):\n    return {'user': user}\n"),),
    ),
    Scenario(
        "Returned dict key renamed",
        True,
        FlightPlan("checkout shape", ("cart/items.py",), changes=("cart.items.checkout",)),
        (("cart/items.py", 'return {"total": cart_total(lines)}', 'return {"amount": cart_total(lines)}'),),
        FlightPlan("receipts", ("cart/receipts.py",), uses=("cart.items.checkout",)),
        (("cart/receipts.py", "",
          "from cart.items import checkout\n\n\ndef receipt(lines):\n    return checkout(lines)['total']\n"),),
    ),
    Scenario(
        "Unrelated changes",
        False,
        FlightPlan("password salt", ("auth/passwords.py",), changes=("auth.passwords.hash_password",)),
        (("auth/passwords.py", 'f"{salt}{password}"', 'f"{salt}:{password}"'),),
        FlightPlan("cart floor", ("cart/totals.py",), changes=("cart.totals.cart_total",)),
        (("cart/totals.py", "return sum(line_total(price, quantity) for price, quantity in lines)",
          "return max(0, sum(line_total(price, quantity) for price, quantity in lines))"),),
    ),
    Scenario(
        "Method gains a parameter vs a new caller",
        True,
        STORE_PLAN,
        OPEN_NEEDS_TTL,
        FlightPlan("refund login", ("billing/refunds.py",), uses=("auth.store.SessionStore",)),
        (("billing/refunds.py", "",
          "from auth.store import SessionStore\n\n\ndef refund_session(user):\n"
          "    store = SessionStore()\n    return store.open(user)\n"),),
        base=(STORE,),
    ),
    Scenario(
        "Method called through an attribute",
        True,
        STORE_PLAN,
        OPEN_NEEDS_TTL,
        FlightPlan("refund service", ("billing/service.py",), uses=("auth.store.SessionStore",)),
        (("billing/service.py", "",
          "from auth.store import SessionStore\n\n\nclass RefundService:\n"
          "    def __init__(self, store: SessionStore):\n        self.store = store\n\n"
          "    def start(self, user):\n        return self.store.open(user)\n"),),
        base=(STORE,),
    ),
    Scenario(
        "Class method renamed",
        True,
        FlightPlan("store naming", ("auth/store.py",), changes=("auth.store.SessionStore.empty",)),
        (("auth/store.py", "def empty(cls):", "def fresh(cls):"),),
        FlightPlan("test login", ("auth/fixtures.py",), uses=("auth.store.SessionStore",)),
        (("auth/fixtures.py", "",
          "from auth.store import SessionStore\n\n\ndef logged_in(user):\n"
          "    store = SessionStore.empty()\n    store.open(user)\n    return store\n"),),
        base=(STORE,),
    ),
    Scenario(
        "Function imported through its package",
        True,
        SESSION_PLAN,
        (("auth/session.py", "def create_session(user):", "def create_session(user, ttl):"),),
        FlightPlan("refunds", ("billing/refunds.py",), uses=("auth.create_session",)),
        (("billing/refunds.py", "",
          "from auth import create_session\n\n\ndef refund(user):\n    return create_session(user)\n"),),
        base=(("auth/__init__.py", "", "from auth.session import create_session, end_session\n"),),
    ),
    Scenario(
        "Arguments swapped",
        True,
        FlightPlan("salt first", ("auth/passwords.py",), changes=("auth.passwords.hash_password",)),
        (("auth/passwords.py", "def hash_password(password, salt):", "def hash_password(salt, password):"),
         ("auth/passwords.py", "return hash_password(password, salt) == stored",
          "return hash_password(salt, password) == stored")),
        FlightPlan("password reset", ("auth/reset.py",), uses=("auth.passwords.hash_password",)),
        (("auth/reset.py", "",
          "from auth.passwords import hash_password\n\n\ndef reset_password(user, password, salt):\n"
          "    return {user: hash_password(password, salt)}\n"),),
    ),
    Scenario(
        "Function made async",
        True,
        FlightPlan("async sessions", ("auth/session.py",), changes=("auth.session.create_session",)),
        (("auth/session.py", "def create_session(user):", "async def create_session(user):"),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Constant renamed vs a new import",
        True,
        FlightPlan("session naming", ("auth/session.py",), changes=("auth.session.SESSIONS",)),
        (("auth/session.py", "SESSIONS", "ACTIVE_SESSIONS"),),
        FlightPlan("admin count", ("auth/admin.py",), uses=("auth.session.SESSIONS",)),
        (("auth/admin.py", "",
          "from auth.session import SESSIONS\n\n\ndef active_count():\n    return len(SESSIONS)\n"),),
    ),
    Scenario(
        "Function moved to another module",
        True,
        FlightPlan("token module", ("auth/session.py", "auth/tokens.py"), changes=("auth.session.create_session",)),
        (("auth/session.py",
          "def create_session(user):\n    token = secrets.token_hex(16)\n"
          "    SESSIONS[token] = user\n    return token\n\n\n", ""),
         ("auth/tokens.py", "",
          "import secrets\n\nfrom auth.session import SESSIONS\n\n\ndef create_session(user):\n"
          "    token = secrets.token_hex(16)\n    SESSIONS[token] = user\n    return token\n")),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Function passed as a callback",
        True,
        SESSION_PLAN,
        RENAME_SESSION,
        FlightPlan("batch login", ("billing/batch.py",), uses=("auth.session.create_session",)),
        (("billing/batch.py", "",
          "from auth.session import create_session\n\n\ndef open_all(users):\n"
          "    return list(map(create_session, users))\n"),),
    ),
    Scenario(
        "Same line of a config file",
        True,
        FlightPlan("short sessions", ("config/settings.toml",)),
        (("config/settings.toml", "ttl = 3600", "ttl = 900"),),
        FlightPlan("long sessions", ("config/settings.toml",)),
        (("config/settings.toml", "ttl = 3600", "ttl = 86400"),),
        base=(SETTINGS,),
    ),
    Scenario(
        "Both create the same new file",
        True,
        FlightPlan("refunds", ("billing/refunds.py",)),
        (("billing/refunds.py", "", "def refund(user):\n    return {'user': user}\n"),),
        FlightPlan("refund issuing", ("billing/refunds.py",)),
        (("billing/refunds.py", "", "def issue_refund(invoice):\n    return -invoice.amount\n"),),
    ),
    Scenario(
        "Different methods of one class",
        False,
        FlightPlan("longer tokens", ("auth/store.py",), changes=("auth.store.SessionStore.open",)),
        (("auth/store.py", "token_hex(16)", "token_hex(32)"),),
        FlightPlan("strict close", ("auth/store.py",), changes=("auth.store.SessionStore.close",)),
        (("auth/store.py", "self.sessions.pop(token, None)", "del self.sessions[token]"),),
        base=(STORE,),
    ),
    Scenario(
        "Optional parameter added",
        False,
        SESSION_PLAN,
        (("auth/session.py", "def create_session(user):", "def create_session(user, ttl=3600):"),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Parameter renamed, caller passes it by position",
        False,
        FlightPlan("naming", ("cart/totals.py",), changes=("cart.totals.line_total",)),
        (("cart/totals.py", "def line_total(price, quantity):\n    return price * quantity",
          "def line_total(unit_price, quantity):\n    return unit_price * quantity"),),
        FlightPlan("quotes", ("cart/quote.py",), uses=("cart.totals.line_total",)),
        (("cart/quote.py", "",
          "from cart.totals import line_total\n\n\ndef quote(price):\n    return line_total(price, 2)\n"),),
    ),
    Scenario(
        "Same name in another module",
        False,
        FlightPlan("currency", ("billing/api.py",), changes=("billing.api.balance",)),
        (("billing/api.py", "def balance(invoices):", "def balance(invoices, currency):"),),
        FlightPlan("wallet", ("cart/wallet.py",)),
        (("cart/wallet.py", "",
          "def balance(lines):\n    return sum(price for price, _ in lines)\n\n\n"
          "def summary(lines):\n    return {'balance': balance(lines)}\n"),),
    ),
    Scenario(
        "Different parts of one config file",
        False,
        FlightPlan("short sessions", ("config/settings.toml",)),
        (("config/settings.toml", "ttl = 3600", "ttl = 900"),),
        FlightPlan("euro billing", ("config/settings.toml",)),
        (("config/settings.toml", 'currency = "USD"', 'currency = "EUR"'),),
        base=(SETTINGS,),
    ),
    Scenario(
        "Body refactor vs a new caller",
        False,
        SESSION_PLAN,
        (("auth/session.py", "secrets.token_hex(16)", "secrets.token_urlsafe(16)"),),
        REFUND_PLAN,
        REFUND_EDIT,
    ),
    Scenario(
        "Another method of the class changes",
        False,
        FlightPlan("close reasons", ("auth/store.py",), changes=("auth.store.SessionStore.close",)),
        (("auth/store.py", "def close(self, token):", "def close(self, token, reason):"),),
        FlightPlan("refund login", ("billing/refunds.py",), uses=("auth.store.SessionStore",)),
        (("billing/refunds.py", "",
          "from auth.store import SessionStore\n\n\ndef refund_session(user):\n"
          "    store = SessionStore()\n    return store.open(user)\n"),),
        base=(STORE,),
    ),
    Scenario(
        "Both add a function with the same name",
        True,
        FlightPlan("refunds", ("billing/api.py",), changes=("billing.api.refund",)),
        (("billing/api.py", "def bill_user(user, amount):",
          "def refund(user):\n    return Invoice(user, -1)\n\n\ndef bill_user(user, amount):"),),
        FlightPlan("refund totals", ("billing/api.py",)),
        (("billing/api.py", 'return {"due": total_due(invoices)}',
          'return {"due": total_due(invoices)}\n\n\ndef refund(invoice):\n    return -invoice.amount'),),
    ),
    Scenario(
        "Both edit one function in different places",
        False,
        FlightPlan("longer tokens", ("auth/session.py",), changes=("auth.session.create_session",)),
        (("auth/session.py", "secrets.token_hex(16)", "secrets.token_hex(32)"),),
        FlightPlan("token logging", ("auth/session.py",), changes=("auth.session.create_session",)),
        (("auth/session.py", "    return token\n\n\ndef end_session", "    return str(token)\n\n\ndef end_session"),),
    ),
    Scenario(
        "Function and its old caller renamed together",
        False,
        FlightPlan("session naming", ("auth/session.py", "billing/login.py"), changes=("auth.session.create_session",)),
        (("auth/session.py", "def create_session(user):", "def open_session(user):"),
         ("billing/login.py", "import create_session", "import open_session"),
         ("billing/login.py", "return create_session(user)", "return open_session(user)")),
        FlightPlan("login audit", ("billing/login.py",)),
        (("billing/login.py", "return {'user': user}", "return {'user': user, 'audited': True}"),),
        base=(("billing/login.py", "",
               "from auth.session import create_session\n\n\ndef login(user):\n    return create_session(user)\n\n\n"
               "def audit(user):\n    return {'user': user}\n"),),
    ),
    Scenario(
        "Same edit on both laptops",
        False,
        FlightPlan("short sessions", ("config/settings.toml",)),
        (("config/settings.toml", "ttl = 3600", "ttl = 900"),),
        FlightPlan("short sessions too", ("config/settings.toml",)),
        (("config/settings.toml", "ttl = 3600", "ttl = 900"),),
        base=(SETTINGS,),
    ),
)
