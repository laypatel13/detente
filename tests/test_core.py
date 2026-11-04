from dataclasses import asdict

import pytest

from backend.contracts import calls, changes, definitions, module_name, problem, reexports
from backend.detector import check_code, check_plan, check_violations
from backend.plans import FlightPlan, PlanError, parse_landed, parse_plan, same_symbol


def signature(source: str, name: str = "m.f"):
    return definitions(source, "m")[name].signature


def call(source: str, path: str = "x.py"):
    return calls(source, path)[0]


def report(*changed, call_list=(), files=()):
    return {"changes": list(changed), "calls": [asdict(c) for c in call_list], "files": list(files)}


def test_parse_plan_reads_every_field():
    plan = parse_plan(
        "FLIGHT PLAN\ntask: refunds\nedit: billing/refunds.py, billing/api.py\n"
        "changes: none\nuses: `auth.session.create_session()`"
    )
    assert plan == FlightPlan(
        "refunds", ("billing/refunds.py", "billing/api.py"), (), ("auth.session.create_session",)
    )


def test_parse_plan_ignores_other_messages():
    assert parse_plan("what's the plan for today?") is None


def test_parse_plan_finds_a_plan_after_chatter():
    assert parse_plan("Filing now.\n**FLIGHT PLAN**\ntask: x\nedit: a.py").edit == ("a.py",)


@pytest.mark.parametrize("body", ["FLIGHT PLAN\nedit: a.py", "FLIGHT PLAN\ntask: x"])
def test_parse_plan_refuses_incomplete_plans(body):
    with pytest.raises(PlanError):
        parse_plan(body)


def test_parse_landed():
    assert parse_landed("LANDED\nfiles: a.py")
    assert not parse_landed("we have landed on a decision")


def test_same_symbol_matches_short_names_only_on_a_boundary():
    assert same_symbol("auth.session.create_session", "create_session")
    assert not same_symbol("auth.session.recreate_session", "create_session")


def test_module_name_handles_src_layout_and_packages():
    assert module_name("src/auth/session.py") == "auth.session"
    assert module_name("auth/__init__.py") == "auth"


def test_signature_marks_required_and_optional():
    parsed = signature("def f(a, b=1, *, c, d=2): pass")
    assert parsed.positional == ("a", "b")
    assert parsed.keyword_only == ("c", "d")
    assert parsed.required == ("a", "c")


def test_constructor_signature_drops_self():
    parsed = signature("class C:\n    def __init__(self, a, b=(1, 2)): pass", "m.C")
    assert parsed.positional == ("a", "b")
    assert parsed.text == "C(a, b=(1, 2))"


def test_dataclass_constructor_comes_from_fields():
    parsed = signature("@dataclass\nclass C:\n    a: int\n    b: int = 1", "m.C")
    assert parsed.positional == ("a", "b")
    assert parsed.required == ("a",)


@pytest.mark.parametrize(
    ("source", "path", "expected"),
    [
        ("from auth.session import create_session\ncreate_session(u)", "b/r.py", "auth.session.create_session"),
        ("from auth.session import create_session as cs\ncs(u)", "b/r.py", "auth.session.create_session"),
        ("from auth import session\nsession.create_session(u)", "b/r.py", "auth.session.create_session"),
        ("import auth.session\nauth.session.create_session(u)", "b/r.py", "auth.session.create_session"),
        ("import auth.session as s\ns.create_session(u)", "b/r.py", "auth.session.create_session"),
        ("from .session import create_session\ncreate_session(u)", "auth/api.py", "auth.session.create_session"),
        ("from ..auth.session import create_session\ncreate_session(u)", "app/billing/r.py", "app.auth.session.create_session"),
        ("def f(): pass\nf()", "auth/session.py", "auth.session.f"),
    ],
)
def test_calls_resolve_through_imports(source, path, expected):
    assert call(source, path).symbol == expected


def test_method_calls_on_unknown_objects_are_skipped():
    assert calls("def f(x):\n    return x.save()", "a.py") == []


@pytest.mark.parametrize(
    ("definition", "invocation", "expected"),
    [
        ("def f(a): pass", "f(1)", None),
        ("def f(a, b): pass", "f(1)", "is missing required argument b"),
        ("def f(a, b=1): pass", "f(1)", None),
        ("def f(a): pass", "f(1, 2)", "passes 2 positional arguments, the function takes 1"),
        ("def f(a): pass", "f(a=1, b=2)", "passes unknown keyword b"),
        ("def f(a, **k): pass", "f(1, b=2)", None),
        ("def f(*a): pass", "f(1, 2, 3)", None),
        ("def f(a, b): pass", "f(*x)", None),
        ("def f(a, b): pass", "f(**x)", None),
        ("def f(a): pass", "f(1, 2, *x)", "passes 2 positional arguments, the function takes 1"),
    ],
)
def test_problem_checks_each_way_a_call_can_break(definition, invocation, expected):
    assert problem(signature(definition), call(f"{definition}\n{invocation}")) == expected


def test_problem_reports_a_missing_name():
    assert problem(None, call("def f(): pass\nf()")) == "calls a name that no longer exists"


def test_changes_skips_untouched_definitions():
    records = changes("def f(a): pass\ndef g(): pass", "def f(a, b): pass\ndef g(): pass", "m.py")
    assert [record["symbol"] for record in records] == ["m.f"]


def test_changes_records_removed_and_added():
    records = {r["symbol"]: r for r in changes("def old(): pass", "def new(): pass", "m.py")}
    assert records["m.old"]["after"] is None
    assert records["m.new"]["before"] is None


def test_check_plan_flags_a_use_of_something_being_changed():
    mine = FlightPlan("refunds", ("billing/refunds.py",), uses=("auth.session.create_session",))
    theirs = FlightPlan("expiry", ("auth/session.py",), changes=("create_session",))
    found = check_plan("a-codex", mine, {"lay-claude": theirs})
    assert [t.reason for t in found] == ["a-codex uses create_session, which lay-claude is changing"]


def test_check_plan_flags_in_both_directions():
    mine = FlightPlan("expiry", ("auth/session.py",), changes=("create_session",))
    theirs = FlightPlan("refunds", ("billing/refunds.py",), uses=("create_session",))
    assert check_plan("lay-claude", mine, {"a-codex": theirs})[0].other == "a-codex"


def test_check_plan_flags_same_file_and_duplicate_work():
    mine = FlightPlan("x", ("api.py",), changes=("POST /refunds",))
    theirs = FlightPlan("y", ("api.py",), changes=("POST /refunds",))
    assert len(check_plan("a", mine, {"b": theirs})) == 2


def test_check_plan_ignores_own_flight_and_unrelated_flights():
    mine = FlightPlan("x", ("a.py",))
    assert check_plan("a", mine, {"a": mine, "b": FlightPlan("y", ("b.py",))}) == []


def hero_reports(caller_source="from auth.session import create_session\ncreate_session(user)\n"):
    changed = changes("def create_session(user): pass", "def create_session(user, ttl): pass", "auth/session.py")
    return {
        "lay-claude": report(*changed),
        "a-codex": report(call_list=calls(caller_source, "billing/refunds.py")),
    }


def test_check_code_catches_a_new_required_argument_across_files():
    collision = check_code(hero_reports())[0]
    assert collision["reason"] == "is missing required argument ttl"
    assert collision["changed_by"] == "lay-claude"
    assert collision["caller"] == "a-codex"
    assert collision["breaks"]["file"] == "billing/refunds.py"
    assert collision["options"][0] == {"key": "A", "text": "Give ttl a default", "agent": "lay-claude"}


def test_check_code_goes_quiet_when_the_caller_is_fixed():
    fixed = "from auth.session import create_session\ncreate_session(user, 30)\n"
    assert check_code(hero_reports(fixed)) == []


def test_check_code_catches_a_deleted_function():
    changed = changes("def f(): pass", "", "m.py")
    reports = {"a": report(*changed), "b": report(call_list=calls("from m import f\nf()", "x.py"))}
    assert check_code(reports)[0]["reason"] == "calls a name that no longer exists"


def test_check_code_ignores_a_compatible_change():
    changed = changes("def f(a): pass", "def f(a, b=1): pass", "m.py")
    reports = {"a": report(*changed), "b": report(call_list=calls("from m import f\nf(1)", "x.py"))}
    assert check_code(reports) == []


def test_check_code_ignores_your_own_calls():
    changed = changes("def f(a): pass", "def f(a, b): pass", "m.py")
    own = calls("from m import f\nf(1)", "x.py")
    assert check_code({"a": report(*changed, call_list=own)}) == []


def test_check_code_catches_two_agents_changing_one_function():
    left = changes("def f(): return 1", "def f(): return 2", "m.py")
    right = changes("def f(): return 1", "def f(): return 3", "m.py")
    found = check_code({"a": report(*left), "b": report(*right)})
    assert [collision["kind"] for collision in found] == ["same_function"]


def test_check_code_collapses_several_calls_in_one_file():
    source = "from auth.session import create_session\ncreate_session(a)\ncreate_session(b)\n"
    assert len(check_code(hero_reports(source))) == 1


def test_check_violations_lists_files_outside_the_clearance():
    plan = FlightPlan("x", ("a.py",))
    assert check_violations(report(files=("a.py", "b.py")), plan) == ["b.py"]


def test_check_violations_flags_everything_with_no_flight():
    assert check_violations(report(files=("a.py",)), None) == ["a.py"]


def test_methods_get_their_own_contract():
    found = definitions(
        "class S:\n    def __init__(self, a): pass\n    def open(self, user, ttl): pass\n"
        "    @staticmethod\n    def make(x): pass",
        "m",
    )
    assert found["m.S"].signature.positional == ("a",)
    assert found["m.S.open"].signature.required == ("user", "ttl")
    assert found["m.S.open"].signature.text == "S.open(user, ttl)"
    assert found["m.S.make"].signature.positional == ("x",)


def test_editing_one_method_leaves_the_class_and_its_other_methods_alone():
    base = "class S:\n    def open(self): return 1\n    def close(self): return 1\n"
    records = changes(base, base.replace("def open(self): return 1", "def open(self): return 2"), "m.py")
    assert [record["symbol"] for record in records] == ["m.S.open"]


def test_module_constants_are_definitions():
    assert "m.SESSIONS" in definitions("SESSIONS: dict = {}\nTTL = 30", "m")


def test_async_is_part_of_the_contract():
    assert signature("async def f(a): pass").is_async


METHOD_CALLS = [
    "from auth.store import Store\ns = Store()\ns.open(u)",
    "from auth.store import Store\ndef f(s: Store):\n    s.open(u)",
    "from auth.store import Store\ndef f(s: 'Store | None'):\n    s.open(u)",
    "from auth.store import Store\nStore().open(u)",
    "from auth.store import Store\nclass R:\n    def __init__(self, s: Store):\n        self.s = s\n"
    "    def go(self):\n        self.s.open(u)",
    "from auth import store\nclass R:\n    def __init__(self):\n        self.s = store.Store()\n"
    "    def go(self):\n        self.s.open(u)",
]


@pytest.mark.parametrize("source", METHOD_CALLS)
def test_method_calls_resolve_through_the_types_in_view(source):
    assert "auth.store.Store.open" in [found.symbol for found in calls(source, "b/r.py")]


def test_self_calls_resolve_to_the_class():
    source = "class S:\n    def a(self):\n        self.b()\n    def b(self): pass"
    assert call(source, "m.py").symbol == "m.S.b"


def test_a_name_with_two_types_is_dropped():
    source = "from a import X, Y\ndef f(flag):\n    s = X()\n    if flag:\n        s = Y()\n    s.open()"
    assert "a.X.open" not in [found.symbol for found in calls(source, "b.py")]


def test_a_parameter_shadows_an_import_with_the_same_name():
    source = "from auth import session\ndef f(session):\n    session.create_session(u)"
    assert calls(source, "b.py")[-1].kind == "import"
    assert len(calls(source, "b.py")) == 1


def test_imports_come_after_calls_and_only_break_when_the_name_goes():
    found = calls("from auth.session import SESSIONS, create_session\ncreate_session(u)", "b.py")
    assert [(item.symbol, item.kind) for item in found] == [
        ("auth.session.create_session", "call"),
        ("auth.session.SESSIONS", "import"),
        ("auth.session.create_session", "import"),
    ]
    assert problem(None, found[1]) == "imports a name that no longer exists"
    assert problem(signature("def f(a): pass"), found[1]) is None


def test_awaited_calls_are_marked():
    source = "from m import f\nasync def g():\n    await f()\n    gather(f())\n    f()"
    found = [item.awaited for item in calls(source, "x.py") if item.kind == "call" and item.symbol == "m.f"]
    assert found == [True, None, False]


def test_reexports_follow_a_package_import_to_the_definition():
    modules = {"auth": ("auth/__init__.py", "from .session import create_session")}
    resolve = reexports(modules.get)
    assert resolve("auth.create_session") == "auth.session.create_session"
    assert resolve("auth.session.create_session") == "auth.session.create_session"
    assert call("from auth import create_session\ncreate_session(u)", "b.py").symbol == "auth.create_session"
    assert calls("from auth import create_session\ncreate_session(u)", "b.py", resolve)[0].symbol == (
        "auth.session.create_session"
    )


@pytest.mark.parametrize(
    ("before", "after", "invocation", "expected"),
    [
        ("def f(a): pass", "async def f(a): pass", "f(1)", "calls it without await, and it's async now"),
        ("def f(a): pass", "async def f(a): pass", "async def g():\n    await f(1)", None),
        ("async def f(a): pass", "def f(a): pass", "async def g():\n    await f(1)", "awaits it, and it isn't async any more"),
        ("def f(a, b): pass", "def f(b, a): pass", "f(1, 2)", "passes a as argument 1, and that's b now"),
        ("def f(a, b): pass", "def f(b, a): pass", "f(a=1, b=2)", None),
        ("def f(a, b): pass", "def f(x, b): pass", "f(1, 2)", None),
    ],
)
def test_problem_compares_against_the_old_contract(before, after, invocation, expected):
    found = [item for item in calls(f"{after}\n{invocation}", "m.py") if item.symbol == "m.f"][0]
    assert problem(signature(after), found, signature(before)) == expected


def file_report(created=(), hunks=None):
    return {"changes": [], "calls": [], "files": [], "created": list(created), "hunks": hunks or {}}


def test_check_code_catches_two_agents_creating_one_file():
    reports = {"a": file_report(created=["new.py"]), "b": file_report(created=["new.py"])}
    assert [c["reason"] for c in check_code(reports)] == ["a and b both created new.py"]


def test_creating_one_file_is_one_clash_not_one_per_function():
    left = changes("", "def f(): pass", "new.py")
    right = changes("", "def f(): return 1", "new.py")
    reports = {
        "a": {**file_report(created=["new.py"]), "changes": left},
        "b": {**file_report(created=["new.py"]), "changes": right},
    }
    assert [c["kind"] for c in check_code(reports)] == ["same_file"]


@pytest.mark.parametrize(
    ("mine", "theirs", "clash"),
    [
        ([2, 3, "x"], [2, 3, "y"], True),
        ([2, 3, "x"], [2, 3, "x"], False),
        ([2, 3, "x"], [3, 4, "y"], True),
        ([2, 3, "x"], [5, 6, "y"], False),
        ([4, 4, "x"], [4, 4, "y"], True),
    ],
)
def test_line_clashes_follow_git(mine, theirs, clash):
    reports = {
        "a": file_report(hunks={"c.toml": {"blob": "1", "lines": [mine]}}),
        "b": file_report(hunks={"c.toml": {"blob": "1", "lines": [theirs]}}),
    }
    assert bool(check_code(reports)) is clash


def test_line_numbers_from_different_versions_are_not_compared():
    reports = {
        "a": file_report(hunks={"c.toml": {"blob": "1", "lines": [[2, 3, "x"]]}}),
        "b": file_report(hunks={"c.toml": {"blob": "2", "lines": [[2, 3, "y"]]}}),
    }
    assert check_code(reports) == []


def test_line_clashes_in_many_files_open_one_conflict():
    hunks = {name: {"blob": name, "lines": [[1, 2, name]]} for name in ("a.yml", "b.yml", "c.yml")}
    other = {name: {**hunk, "lines": [[1, 2, "other"]]} for name, hunk in hunks.items()}
    found = check_code({"a": file_report(hunks=hunks), "b": file_report(hunks=other)})
    assert [c["reason"] for c in found] == ["a and b both changed a.yml at line 1 and 2 other files"]


def py_report(before, after, path, lines, blob="1"):
    return {
        "changes": changes(before, after, path),
        "calls": [],
        "files": [path],
        "created": {},
        "hunks": {path: {"blob": blob, "lines": lines}},
    }


BASE = "def f():\n    a = 1\n    b = 2\n    c = 3\n    return a\n"


def test_edits_in_different_places_of_one_function_pass_when_lines_can_be_compared():
    left = py_report(BASE, BASE.replace("a = 1", "a = 9"), "m.py", [[2, 3, "x"]])
    right = py_report(BASE, BASE.replace("c = 3", "c = 9"), "m.py", [[4, 5, "y"]])
    assert check_code({"a": left, "b": right}) == []


def test_edits_on_the_same_line_are_named_after_the_function():
    left = py_report(BASE, BASE.replace("a = 1", "a = 9"), "m.py", [[2, 3, "x"]])
    right = py_report(BASE, BASE.replace("a = 1", "a = 8"), "m.py", [[2, 3, "y"]])
    [collision] = check_code({"a": left, "b": right})
    assert (collision["kind"], collision["reason"], collision["breaks"]["line"]) == (
        "same_function", "a and b both changed f", 2
    )


def test_different_starting_versions_fall_back_to_any_shared_change():
    left = py_report(BASE, BASE.replace("a = 1", "a = 9"), "m.py", [[2, 3, "x"]], blob="1")
    right = py_report(BASE, BASE.replace("c = 3", "c = 9"), "m.py", [[4, 5, "y"]], blob="2")
    assert [c["kind"] for c in check_code({"a": left, "b": right})] == ["same_function"]


def test_two_new_definitions_of_one_name_stop_even_far_apart():
    left = py_report(BASE, "def g(): pass\n" + BASE, "m.py", [[1, 1, "x"]])
    right = py_report(BASE, BASE + "def g(): return 1\n", "m.py", [[6, 6, "y"]])
    assert [c["reason"] for c in check_code({"a": left, "b": right})] == ["a and b both changed g"]


def test_the_same_function_edit_on_both_laptops_passes():
    edited = BASE.replace("a = 1", "a = 9")
    reports = {"a": report(*changes(BASE, edited, "m.py")), "b": report(*changes(BASE, edited, "m.py"))}
    assert check_code(reports) == []


def test_calls_can_be_limited_to_the_lines_this_work_wrote():
    source = "from m import f\nf(1)\nf(2,\n  3)\n"
    assert [found.code for found in calls(source, "x.py", lines=[[3, 4]])] == ["f(2, 3)"]
    assert [found.code for found in calls(source, "x.py", lines=[[4, 5]])] == ["f(2, 3)"]
    assert calls(source, "x.py", lines=[]) == []
