"""Plant real breaks in real projects and check that Detente stops them. Offline.

    make bench-planted REPOS="~/code/django ~/code/flask"

For each project, a fixed seed picks functions that another file really calls. For each
one, laptop A changes the function and laptop B adds a new call, copied from a real call
site, both unpushed on top of the same commit. Five of the changes break B's call for
certain; two leave it working. git merge-tree and file leases see two different files.

Three tiers: functions imported from the module that defines them, functions imported
through a package's __init__ (from flask import url_for), and methods, called on an
object whose type B's code states.

Picking targets doesn't use Detente: it reads the code with Python's ast, the way the
interpreter resolves imports. Each repo is cloned into a temporary folder first, so your
own checkout isn't touched, and no project code is run.
"""

import argparse
import ast
import copy
import random
import re
import shutil
import subprocess
import tempfile
import textwrap
import time
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from backend.detector import check_code
from pilot.squawk import Reporter, changed_files

RESULTS = Path(__file__).resolve().parent / "planted.md"
SEED = 1107  # fixed, so every run picks the same functions
PER_REPO = 10
# Targets come from the library itself. Callers can be anywhere, tests included.
NOT_LIBRARY = {"tests", "test", "testing", "docs", "docs_src", "examples", "scripts", "benchmarks", "tools"}
NEW_PARAM = "detente_flag"
CALLER = "detente_planted_caller"
OBJECT = "detente_obj"
TYPE = "DetentePlantedType"
FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)
MOST_HOPS = 3

# (key, label). "direct" is the first table; the other two are the harder cases.
TIERS = [
    ("direct", "Imported from where it's defined"),
    ("reexported", "Imported through a package's __init__"),
    ("method", "Method on a typed object"),
]

# (key, what laptop A does, whether it breaks B's new call for certain)
KINDS = [
    ("required_param", "New required parameter", True),
    ("renamed", "Function renamed", True),
    ("deleted", "Function deleted", True),
    ("made_async", "Function made async", True),
    ("keyword_renamed", "Keyword argument renamed", True),
    ("optional_param", "Optional parameter added", False),
    ("body_changed", "Body changed, signature kept", False),
]


class Skip(Exception):
    """This change doesn't apply to this function."""


@dataclass
class Target:
    module: str
    name: str
    path: str  # where it's defined
    node: ast.FunctionDef | ast.AsyncFunctionDef
    caller: str  # the file laptop B adds a call to
    call: ast.Call
    call_text: str
    tier: str = "direct"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, errors="replace")


def commit(root: Path) -> str:
    # Plain commits: no hooks or signing from the person's own git config.
    git(root, "-c", "user.name=bench", "-c", "user.email=bench@example.invalid", "-c", "commit.gpgsign=false",
        "-c", "core.hooksPath=/dev/null", "commit", "-q", "-a", "-m", "planted")
    return git(root, "rev-parse", "HEAD").stdout.strip()


def parse(source: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source)


def module_of(path: str) -> str:
    name = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return name.removesuffix(".__init__")


def is_library(path: str) -> bool:
    parts = path.split("/")
    return not (set(parts[:-1]) & NOT_LIBRARY) and not parts[-1].startswith("test_")


def read_all(root: Path) -> dict[str, tuple[str, ast.Module]]:
    found = {}
    for path in git(root, "ls-files", "*.py").stdout.splitlines():
        try:
            source = (root / path).read_text()
            found[path] = (source, parse(source))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            continue
    return found


def definitions(files: dict) -> dict[tuple[str, str], tuple[str, ast.AST]]:
    """Plain module-level functions: no decorators, no dunder names, defined once."""
    found, seen = {}, Counter()
    for path, (_, tree) in files.items():
        if not is_library(path):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                seen[(module_of(path), node.name)] += 1
                if not node.decorator_list and not node.name.startswith("__"):
                    found[(module_of(path), node.name)] = (path, node)
    return {key: value for key, value in found.items() if seen[key] == 1}


def from_base(node: ast.ImportFrom, path: str) -> str:
    package = path.removeprefix("src/").split("/")[:-1]
    base = node.module or ""
    if node.level:
        parent = package[: len(package) - node.level + 1]
        base = ".".join([*parent, base] if base else parent)
    return base


def bindings(path: str, tree: ast.Module, modules: set[str]) -> dict[str, tuple[str, str]]:
    """Local name -> ("func", module.name) or ("module", module), as Python would bind it."""
    names: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    names[alias.asname] = ("module", alias.name)
                else:
                    top = alias.name.split(".")[0]
                    names[top] = ("module", top)
        elif isinstance(node, ast.ImportFrom):
            base = from_base(node, path)
            for alias in node.names:
                local = alias.asname or alias.name
                full = f"{base}.{alias.name}"
                names[local] = ("module", full) if full in modules else ("func", full)
    return names


def dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and (head := dotted(node.value)):
        return f"{head}.{node.attr}"
    return None


def plain_call(call: ast.Call) -> bool:
    """No unpacking, so the call's shape is exactly what it says."""
    if any(isinstance(arg, ast.Starred) for arg in call.args) or any(kw.arg is None for kw in call.keywords):
        return False
    return not any(isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom)) for node in ast.walk(call))


def call_sites(files: dict, defined: dict) -> tuple[dict, dict]:
    """Real calls to each function from another file, split by how the caller imports it:
    from the defining module, or through a module that only imports it (a package's
    __init__), followed the way Python binds the name."""
    modules = {module_of(path) for path in files}
    by_module = {module_of(path): path for path in files}

    def follow(key: tuple[str, str], hops: int = 0) -> tuple[tuple[str, str], int]:
        path = by_module.get(key[0])
        if key in defined or hops == MOST_HOPS or path is None:
            return key, hops
        # The module's last top-level binding of the name wins, as it does in Python.
        last = None
        for node in files[path][1].body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*" and (alias.asname or alias.name) == key[1]:
                        last = (from_base(node, path), alias.name)
            elif isinstance(node, (*FUNCTION, ast.ClassDef)) and node.name == key[1]:
                last = None
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(target, ast.Name) and target.id == key[1] for target in targets):
                    last = None
        return follow(last, hops + 1) if last else (key, hops)

    direct: dict[tuple[str, str], list] = {}
    reexported: dict[tuple[str, str], list] = {}
    for path, (source, tree) in files.items():
        names = bindings(path, tree, modules)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not (name := dotted(node.func)):
                continue
            head, _, rest = name.partition(".")
            if head not in names:
                continue
            kind, where = names[head]
            if kind == "func" and not rest:
                module, _, func = where.rpartition(".")
            elif kind == "module" and rest:
                module, _, func = f"{where}.{rest}".rpartition(".")
            else:
                continue
            key, hops = follow((module, func))
            if key in defined and defined[key][0] != path and plain_call(node):
                text = ast.get_source_segment(source, node)
                if text:
                    (reexported if hops else direct).setdefault(key, []).append((path, node, text))
    return direct, reexported


def methods(files: dict) -> dict[tuple[str, str], tuple[str, ast.AST]]:
    """Plain methods of top-level library classes, whose name no other class or function
    in the project uses, so a call of that name elsewhere is a call of this method."""
    found, seen = {}, Counter()
    for path, (_, tree) in files.items():
        for node in tree.body:
            if isinstance(node, FUNCTION):
                seen[node.name] += 1
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if not isinstance(item, FUNCTION):
                        continue
                    seen[item.name] += 1
                    plain = not item.decorator_list and not item.name.startswith("__")
                    if is_library(path) and plain and (item.args.posonlyargs or item.args.args):
                        found[(module_of(path), f"{node.name}.{item.name}")] = (path, item)
    return {key: value for key, value in found.items() if seen[key[1].split(".")[1]] == 1}


def method_sites(files: dict, defined: dict) -> dict[tuple[str, str], list]:
    """Real calls of each method from another file. B's copy calls it on a typed object."""
    modules = {module_of(path) for path in files}
    by_name = {key[1].split(".")[1]: key for key in defined}
    found: dict[tuple[str, str], list] = {}
    for path, (_, tree) in files.items():
        names = bindings(path, tree, modules)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            key = by_name.get(node.func.attr)
            if key is None or defined[key][0] == path or not plain_call(node):
                continue
            # Skip a module's function of the same name, and calls through the class itself.
            receiver = (dotted(node.func.value) or "").split(".")
            if names.get(receiver[0], ("",))[0] == "module" or receiver[-1] == key[1].split(".")[0]:
                continue
            call = copy.deepcopy(node)
            call.func = ast.Attribute(ast.Name(OBJECT), node.func.attr)
            found.setdefault(key, []).append((path, node, ast.unparse(call)))
    return found


def fits(node: ast.AST, call: ast.Call, method: bool) -> bool:
    """Whether the call binds to the function as it is at the base, the way Python binds it."""
    args = node.args
    posonly = [arg.arg for arg in args.posonlyargs]
    named = [arg.arg for arg in args.args]
    positional = [*posonly, *named][1:] if method else [*posonly, *named]
    posonly = posonly[1:] if method and posonly else posonly
    if len(call.args) > len(positional) and not args.vararg:
        return False
    filled = set(positional[: len(call.args)])
    for keyword in call.keywords:
        known = keyword.arg in {*positional[len(posonly) :], *(arg.arg for arg in args.kwonlyargs)}
        if keyword.arg in filled or not (known or args.kwarg):
            return False
        filled.add(keyword.arg)
    required = positional[: len(positional) - len(args.defaults)]
    required += [arg.arg for arg, default in zip(args.kwonlyargs, args.kw_defaults) if default is None]
    return all(name in filled for name in required)


def caller_source(source: str, target: Target) -> str:
    awaits = isinstance(target.node, ast.AsyncFunctionDef)
    head, call = ("async def", f"await {target.call_text}") if awaits else ("def", target.call_text)
    if target.tier == "method":
        cls = target.name.split(".")[0]
        new = f"\n\nfrom {target.module} import {cls} as {TYPE}\n\n\n{head} {CALLER}({OBJECT}: {TYPE}):\n    return {call}\n"
    else:
        new = f"\n\n{head} {CALLER}():\n    return {call}\n"
    return (source if source.endswith("\n") else source + "\n") + new


def pick(files: dict, defined: dict, sites: dict, rng: random.Random, tier: str, taken: set = frozenset()) -> list[Target]:
    keys = sorted(key for key in sites if key not in taken)
    rng.shuffle(keys)
    chosen: list[Target] = []
    used_modules: set[str] = set()
    # Spread across modules first, then fill up.
    for spread in (True, False):
        for key in keys:
            if len(chosen) == PER_REPO or any((t.module, t.name) == key for t in chosen):
                continue
            if spread and key[0] in used_modules:
                continue
            path, node = defined[key]
            # Prefer a caller outside the tests, the way a teammate writes product code.
            options = sorted(sites[key], key=lambda site: (not is_library(site[0]), site[0], site[1].lineno))
            for caller, call, text in options:
                if not fits(node, call, tier == "method"):
                    continue
                target = Target(key[0], key[1], path, node, caller, call, text, tier)
                try:
                    parse(caller_source(files[caller][0], target))
                except SyntaxError:
                    continue
                chosen.append(target)
                used_modules.add(key[0])
                break
    return chosen


def targets(files: dict, name: str) -> list[Target]:
    defined = definitions(files)
    direct, reexported = call_sites(files, defined)
    found = pick(files, defined, direct, random.Random(f"{SEED}-{name}"), "direct")
    taken = {(t.module, t.name) for t in found}
    found += pick(files, defined, reexported, random.Random(f"{SEED}-{name}-reexported"), "reexported", taken)
    own = methods(files)
    found += pick(files, own, method_sites(files, own), random.Random(f"{SEED}-{name}-method"), "method")
    return found


def mutate(kind: str, target: Target) -> ast.AST | None:
    """Laptop A's new version of the function, or None when it's deleted."""
    node = copy.deepcopy(target.node)
    args = node.args
    if kind == "required_param":
        args.kwonlyargs.append(ast.arg(NEW_PARAM))
        args.kw_defaults.append(None)
    elif kind == "optional_param":
        args.kwonlyargs.append(ast.arg(NEW_PARAM))
        args.kw_defaults.append(ast.Constant(None))
    elif kind == "renamed":
        node.name = f"{node.name}_renamed"
    elif kind == "deleted":
        return None
    elif kind == "made_async":
        if isinstance(node, ast.AsyncFunctionDef):
            raise Skip
        node = ast.AsyncFunctionDef(**{field: getattr(node, field, None) for field in node._fields})
    elif kind == "keyword_renamed":
        # Only when the call passes a parameter by name and nothing catches stray keywords.
        params = {arg.arg for arg in [*args.args, *args.kwonlyargs]}
        named = [kw.arg for kw in target.call.keywords if kw.arg in params]
        if not named or args.kwarg:
            raise Skip
        old, new = named[0], f"{named[0]}_renamed"
        for arg in [*args.args, *args.kwonlyargs]:
            if arg.arg == old:
                arg.arg = new
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Name) and child.id == old:
                child.id = new
    elif kind == "body_changed":
        docstring = ast.get_docstring(node, clean=False) is not None
        node.body.insert(1 if docstring else 0, ast.parse("detente_trace = None").body[0])
    return node


def replace(source: str, node: ast.AST, new: ast.AST | None) -> str:
    lines = source.splitlines(keepends=True)
    indent = lines[node.lineno - 1][: node.col_offset]  # a method keeps its class's indent
    text = "" if new is None else textwrap.indent(ast.unparse(ast.fix_missing_locations(new)), indent) + "\n"
    return "".join([*lines[: node.lineno - 1], text, *lines[node.end_lineno :]])


def laptop(root: Path, base: str, path: str, source: str) -> tuple[str, dict]:
    (root / path).write_text(source)
    tip = commit(root)
    return tip, Reporter(root).report(changed_files(root, base), base)


def run(source: Path) -> dict:
    work = Path(tempfile.mkdtemp(prefix="detente-planted-"))
    try:
        repo = work / "clone"
        git(work, "clone", "-q", "--no-checkout", str(source), str(repo))
        left, right = work / "a", work / "b"
        for root in (left, right):
            git(repo, "worktree", "add", "-q", "--detach", str(root), "HEAD")
        base = git(repo, "rev-parse", "HEAD").stdout.strip()
        files = read_all(left)
        chosen = targets(files, source.name)
        rows, slowest = [], 0.0
        for target in chosen:
            print(f"{source.name} [{target.tier}]: {target.module}.{target.name}, called from {target.caller}", flush=True)
            for kind, _, breaks in KINDS:
                try:
                    new = replace(files[target.path][0], target.node, mutate(kind, target))
                    parse(new)
                except (Skip, SyntaxError, ValueError):
                    continue
                for root in (left, right):
                    git(root, "reset", "-q", "--hard", base)
                    git(root, "clean", "-fdq")
                started = time.perf_counter()
                tip_a, mine = laptop(left, base, target.path, new)
                tip_b, theirs = laptop(right, base, target.caller, caller_source(files[target.caller][0], target))
                collisions = check_code({"laptop-a": mine, "laptop-b": theirs})
                slowest = max(slowest, time.perf_counter() - started)
                rows.append(
                    {
                        "symbol": f"{target.module}.{target.name}",
                        "caller": target.caller,
                        "tier": target.tier,
                        "kind": kind,
                        "breaks": breaks,
                        "textual": git(repo, "merge-tree", "--write-tree", tip_a, tip_b).returncode != 0,
                        "collisions": collisions,
                    }
                )
        counts = Counter(target.tier for target in chosen)
        return {"name": source.name, "head": base[:10], "targets": counts, "rows": rows, "slowest": slowest}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def write_results(runs: list[dict]) -> str:
    def count(rows: list, test) -> int:
        return sum(1 for row in rows if test(row))

    def tally(rows: list) -> tuple[list, list]:
        return [row for row in rows if row["breaks"]], [row for row in rows if not row["breaks"]]

    labels = dict(TIERS)
    lines = [
        "# Planted breaks in real projects",
        "",
        "Generated by `make bench-planted`. A fixed seed picks up to "
        f"{PER_REPO} functions in each project that another file",
        "really calls. For each, laptop A changes the function and laptop B adds one new call,",
        "copied from a real call site, both unpushed on top of the same commit. The two",
        "laptops always touch different files.",
        "",
        "| Project | At commit | Functions | Breaks planted | git merge-tree flagged | File leases flagged | Detente stopped | Harmless changes | Detente stopped those | Slowest check |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        broken, fine = tally([row for row in run["rows"] if row["tier"] == "direct"])
        lines.append(
            f"| {run['name']} | `{run['head']}` | {run['targets']['direct']} | {len(broken)} | "
            f"{count(broken, lambda r: r['textual'])} | 0 | {count(broken, lambda r: r['collisions'])} | "
            f"{len(fine)} | {count(fine, lambda r: r['collisions'])} | {run['slowest']:.2f}s |"
        )
    lines += [
        "",
        "## Harder cases",
        "",
        "The same changes, on two kinds of call the first table leaves out. Through `__init__`:",
        "B's call reaches the function through a package that only imports it, as",
        "`from flask import url_for` does. Method: B's call is a method on an object whose type",
        f"B's code states, `def {CALLER}({OBJECT}: Session): return {OBJECT}.send(...)`.",
        "",
        "| Project | Kind of call | Picked | Breaks planted | git merge-tree flagged | Detente stopped | Harmless changes | Detente stopped those |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        for tier in ("reexported", "method"):
            broken, fine = tally([row for row in run["rows"] if row["tier"] == tier])
            lines.append(
                f"| {run['name']} | {labels[tier]} | {run['targets'][tier]} | {len(broken)} | "
                f"{count(broken, lambda r: r['textual'])} | {count(broken, lambda r: r['collisions'])} | "
                f"{len(fine)} | {count(fine, lambda r: r['collisions'])} |"
            )
    every = [row for run in runs for row in run["rows"]]
    lines += [
        "",
        "## By change, all three kinds of call",
        "",
        "| What laptop A did | Breaks B's call? | Planted | Detente stopped | What Detente said |",
        "| --- | --- | --- | --- | --- |",
    ]
    for kind, label, breaks in KINDS:
        rows = [row for row in every if row["kind"] == kind]
        said = Counter(
            re.sub(r"(keyword) \w+", r"\1 <name>", collision["reason"].replace(NEW_PARAM, "<new>"))
            for row in rows
            for collision in row["collisions"]
        )
        reasons = "; ".join(f"{reason} ({n})" for reason, n in said.most_common()) or "nothing"
        lines.append(
            f"| {label} | {'yes' if breaks else 'no'} | {len(rows)} | {count(rows, lambda r: r['collisions'])} | {reasons} |"
        )

    lines.append("")
    for tier, label in TIERS:
        broken, fine = tally([row for row in every if row["tier"] == tier])
        lines.append(
            f"- {label}: Detente stopped {count(broken, lambda r: r['collisions'])} of {len(broken)} "
            f"planted breaks and {count(fine, lambda r: r['collisions'])} of {len(fine)} harmless changes."
        )
    missed = [row for row in every if row["breaks"] and not row["collisions"]]
    false = [row for row in every if not row["breaks"] and row["collisions"]]
    if missed:
        lines += ["", "Breaks it missed:", ""]
        lines += [
            f"- `{row['symbol']}`, {row['kind'].replace('_', ' ')}, called from `{row['caller']}` ({labels[row['tier']]})"
            for row in missed
        ]
    if false:
        lines += ["", "Harmless changes it stopped:", ""]
        for row in false:
            reasons = "; ".join(collision["reason"] for collision in row["collisions"])
            lines.append(f"- `{row['symbol']}`, {row['kind'].replace('_', ' ')} ({labels[row['tier']]}): {reasons}")
    lines += [
        "",
        "How the cases are made:",
        "",
        "- Functions are plain module-level functions with no decorators. In the first table,",
        "  the caller imports them from the module that defines them. Through `__init__`, it",
        "  imports them from a module that only imports them, followed the way Python binds",
        "  the name; star imports aren't followed.",
        "- Methods have no decorators and belong to a top-level class, and no other class or",
        "  function in the project uses their name. B's arguments are copied from a real call",
        "  of that name in another file, which can be on another type, such as a dict's",
        "  `keys()`. B makes the call on an object typed with the class. An object returned by a",
        "  function, or an inherited method, isn't planted: Detente can't see those types (see",
        "  the README's limits).",
        "- B's copied call is checked to fit the function as it is before any change, the way",
        "  Python binds arguments. Calls that unpack `*args` or `**kwargs` are skipped, so",
        "  whether B's call breaks is certain from the code alone. \"Keyword argument renamed\"",
        "  is planted only when the call passes that argument by name and the function has no",
        "  `**kwargs`.",
        "- Laptop A changes only the definition and laptop B only adds a call, so git and",
        "  file leases see two unrelated files. Every break here merges cleanly in git.",
        "- \"Body changed\" keeps the signature, so B's call still runs. It can still change",
        "  behavior, which no code check can promise about.",
        "- Picking functions reads the code with Python's `ast`, not Detente, and no",
        "  project code is run.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="+", type=Path)
    args = parser.parse_args()
    runs = [run(repo.expanduser().resolve()) for repo in args.repos]
    text = write_results(runs)
    RESULTS.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
