"""Read Python contracts with ast: what each function accepts, and how it's called.

Only the standard library, so the squawk daemon can run this on any laptop.
"""

import ast
import copy
import hashlib
import warnings
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from typing import Any

FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)
MOST_HOPS = 5


@dataclass(frozen=True)
class Signature:
    symbol: str
    text: str
    positional: tuple[str, ...]
    keyword_only: tuple[str, ...]
    required: tuple[str, ...]
    varargs: bool = False
    varkw: bool = False
    is_async: bool = False


@dataclass(frozen=True)
class Definition:
    signature: Signature
    fingerprint: str
    lines: tuple[int, int] = (0, 0)  # [first, last + 1), decorators included


@dataclass(frozen=True)
class Call:
    symbol: str
    file: str
    line: int
    code: str
    positional: int
    keywords: tuple[str, ...]
    open_ended: bool  # *args or **kwargs at the call, so counts can't be trusted
    awaited: bool | None = False  # None when the result goes straight into another call
    kind: str = "call"  # "import" only breaks if the name goes away


def _parse(source: str, mode: str = "exec") -> ast.AST:
    # A file with an odd escape like "\d" parses fine but would warn on every poll.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source, mode=mode)


def module_name(path: str) -> str:
    name = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return name.removesuffix(".__init__")


def _signature(
    symbol: str, display: str, args: ast.arguments, method: bool, is_async: bool = False
) -> Signature:
    if method:
        args = copy.copy(args)
        if args.posonlyargs:
            args.posonlyargs = args.posonlyargs[1:]
        else:
            args.args = args.args[1:]

    positional = [arg.arg for arg in [*args.posonlyargs, *args.args]]
    required = positional[: len(positional) - len(args.defaults)]
    required += [
        arg.arg for arg, default in zip(args.kwonlyargs, args.kw_defaults) if default is None
    ]
    return Signature(
        symbol=symbol,
        text=f"{display}({ast.unparse(args)})",
        positional=tuple(positional),
        keyword_only=tuple(arg.arg for arg in args.kwonlyargs),
        required=tuple(required),
        varargs=args.vararg is not None,
        varkw=args.kwarg is not None,
        is_async=is_async,
    )


def _function_signature(symbol: str, display: str, node: ast.AST, method: bool) -> Signature:
    return _signature(symbol, display, node.args, method, isinstance(node, ast.AsyncFunctionDef))


def _dataclass_signature(symbol: str, node: ast.ClassDef) -> Signature:
    fields = [
        statement
        for statement in node.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    ]
    names = [field.target.id for field in fields]
    return Signature(
        symbol=symbol,
        text=f"{node.name}({', '.join(names)})",
        positional=tuple(names),
        keyword_only=(),
        required=tuple(field.target.id for field in fields if field.value is None),
    )


def _class_signature(symbol: str, node: ast.ClassDef) -> Signature:
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            return _signature(symbol, node.name, item.args, method=True)
    if any("dataclass" in ast.unparse(decorator) for decorator in node.decorator_list):
        return _dataclass_signature(symbol, node)
    return Signature(symbol, f"{node.name}()", (), (), ())


def _fingerprint(node: ast.AST) -> str:
    return hashlib.sha256(ast.dump(node).encode()).hexdigest()[:16]


def _lines(node: ast.AST) -> tuple[int, int]:
    first = min([node.lineno, *(item.lineno for item in getattr(node, "decorator_list", []))])
    return first, node.end_lineno + 1


def _is_static(node: ast.AST) -> bool:
    return any(ast.unparse(decorator) == "staticmethod" for decorator in node.decorator_list)


def _assigned_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def definitions(source: str, module: str) -> dict[str, Definition]:
    """Top-level functions, classes with their methods, and module constants.

    A class's contract is its constructor, so the class's own fingerprint leaves the
    other methods out: two agents editing different methods don't touch one thing.
    """
    found: dict[str, Definition] = {}
    for node in _parse(source).body:
        if isinstance(node, FUNCTION):
            symbol = f"{module}.{node.name}"
            signature = _function_signature(symbol, node.name, node, method=False)
            found[symbol] = Definition(signature, _fingerprint(node), _lines(node))
        elif isinstance(node, ast.ClassDef):
            symbol = f"{module}.{node.name}"
            methods = [item for item in node.body if isinstance(item, FUNCTION) and item.name != "__init__"]
            shell = copy.copy(node)
            shell.body = [item for item in node.body if item not in methods]
            found[symbol] = Definition(_class_signature(symbol, node), _fingerprint(shell), _lines(node))
            for method in methods:
                name = f"{symbol}.{method.name}"
                display = f"{node.name}.{method.name}"
                signature = _function_signature(name, display, method, method=not _is_static(method))
                found[name] = Definition(signature, _fingerprint(method), _lines(method))
        else:
            for name in _assigned_names(node):
                symbol = f"{module}.{name}"
                value = Signature(symbol, name, (), (), ())
                found[symbol] = Definition(value, _fingerprint(node), _lines(node))
    return found


def _from_base(node: ast.ImportFrom, package: list[str]) -> str:
    base = node.module or ""
    if node.level:
        parent = package[: len(package) - node.level + 1]
        base = ".".join([*parent, base] if base else parent)
    return base


def _imports(tree: ast.Module, path: str) -> dict[str, str]:
    package = path.removeprefix("src/").split("/")[:-1]
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                names[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom):
            base = _from_base(node, package)
            for alias in node.names:
                names[alias.asname or alias.name] = f"{base}.{alias.name}"
    return names


def reexports(read: Callable[[str], tuple[str, str] | None]) -> Callable[[str], str]:
    """Follow a name back to where it's defined, through modules that only import it.

    `read(module)` gives (path, source) for a module in the checkout, or None. So when
    auth/__init__.py imports create_session from auth.session, `auth.create_session`
    becomes `auth.session.create_session`, the name a change to it is filed under.
    """
    known: dict[str, dict[str, str] | None] = {}

    def imported(module: str) -> dict[str, str] | None:
        if module not in known:
            found = read(module)
            try:
                known[module] = _imports(_parse(found[1]), found[0]) if found else None
            except (SyntaxError, ValueError):
                known[module] = None
        return known[module]

    def resolve(symbol: str, hops: int = 0) -> str:
        parts = symbol.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            names = imported(".".join(parts[:cut]))
            if names is None:
                continue
            target = names.get(parts[cut])
            if target is None or target == ".".join(parts[: cut + 1]) or hops == MOST_HOPS:
                return symbol
            return resolve(".".join([target, *parts[cut + 1 :]]), hops + 1)
        return symbol

    return resolve


def _own_nodes(nodes: list[ast.AST]) -> Iterator[ast.AST]:
    """Nodes of one scope, in order, without the insides of nested functions or classes."""
    for node in nodes:
        yield node
        if not isinstance(node, (*FUNCTION, ast.ClassDef, ast.Lambda)):
            yield from _own_nodes(list(ast.iter_child_nodes(node)))


def _assignments(node: ast.AST) -> Iterator[tuple[ast.expr, ast.expr | None, ast.expr | None]]:
    """(target, value, annotation) for each name this node binds."""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Tuple | ast.List):
                for element in target.elts:
                    yield element, None, None
            else:
                yield target, node.value, None
    elif isinstance(node, ast.AnnAssign):
        yield node.target, node.value, node.annotation
    elif isinstance(node, ast.NamedExpr):
        yield node.target, node.value, None
    elif isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
        yield node.target, None, None
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        yield node.optional_vars, None, None


def _settle(types: dict[str, str | None], name: str, kind: str | None) -> None:
    """A name given two different types is dropped, never guessed."""
    types[name] = kind if types.get(name, kind) == kind else None


class _Calls(ast.NodeVisitor):
    """Names every call it can, through imports and the types it can see.

    A type is known when a name is annotated, or assigned from a call to a known class:
    after `store = SessionStore()`, `store.open()` is SessionStore.open. Attributes set
    on self in any method count too, so `self.store.open()` resolves the same way.
    """

    def __init__(
        self,
        tree: ast.Module,
        path: str,
        resolve: Callable[[str], str],
        lines: list[list[int]] | None,
    ) -> None:
        self.path = path
        self.lines = lines
        self.module = module_name(path)
        self.resolve = resolve
        self.imports = _imports(tree, path)
        self.local = {node.name for node in tree.body if isinstance(node, (*FUNCTION, ast.ClassDef))}
        self.scopes: list[dict[str, str | None]] = []
        self.classes: list[tuple[str, list[ast.AST]]] = []
        self.attributes: dict[str, dict[str, str]] = {}
        self.awaited: dict[int, bool | None] = {}
        self.found: list[Call] = []
        self.imported: list[Call] = []
        self.scopes.append(self._types(tree.body))

    def symbol_of(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            for scope in reversed(self.scopes):
                if node.id in scope:
                    return scope[node.id]
            if node.id in self.imports:
                return self.imports[node.id]
            return f"{self.module}.{node.id}" if node.id in self.local else None
        if isinstance(node, ast.Attribute):
            base = self.symbol_of(node.value)
            if base is None:
                return None
            return self.attributes.get(base, {}).get(node.attr, f"{base}.{node.attr}")
        if isinstance(node, ast.Call):
            return self.symbol_of(node.func)
        if isinstance(node, ast.Await):
            return self.symbol_of(node.value)
        return None

    def _annotation(self, node: ast.expr | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                node = _parse(node.value, mode="eval").body
            except SyntaxError:
                return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            sides = [side for side in (node.left, node.right) if not _is_none(side)]
            return self._annotation(sides[0]) if len(sides) == 1 else None
        if isinstance(node, ast.Subscript) and ast.unparse(node.value).endswith("Optional"):
            return self._annotation(node.slice)
        return self.symbol_of(node) if isinstance(node, ast.Name | ast.Attribute) else None

    def _type_of(self, value: ast.expr | None, annotation: ast.expr | None) -> str | None:
        if annotation is not None:
            return self._annotation(annotation)
        if isinstance(value, ast.Call | ast.Name | ast.Attribute | ast.Await):
            return self.symbol_of(value)
        return None

    def _types(self, body: list[ast.AST], function: ast.AST | None = None) -> dict[str, str | None]:
        types: dict[str, str | None] = {}
        if function is not None:
            args = function.args
            positional = [*args.posonlyargs, *args.args]
            for arg in [*positional, *args.kwonlyargs, args.vararg, args.kwarg]:
                if arg is not None:
                    types[arg.arg] = self._annotation(arg.annotation)
            in_class = self.classes and function in self.classes[-1][1]
            if in_class and positional and not _is_static(function):
                types[positional[0].arg] = self.classes[-1][0]
        self.scopes.append(types)
        for node in _own_nodes(body):
            for target, value, annotation in _assignments(node):
                if isinstance(target, ast.Name):
                    _settle(types, target.id, self._type_of(value, annotation))
        self.scopes.pop()
        return types

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in [*node.decorator_list, *node.bases]:
            self.visit(decorator)
        symbol = f"{self.module}.{node.name}"
        methods = [item for item in node.body if isinstance(item, FUNCTION)]
        self.classes.append((symbol, methods))

        attributes: dict[str, str | None] = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                _settle(attributes, item.target.id, self._annotation(item.annotation))
        for method in methods:
            positional = [*method.args.posonlyargs, *method.args.args]
            if not positional or _is_static(method):
                continue
            self.scopes.append(self._types(method.body, method))
            for inner in _own_nodes(method.body):
                for target, value, annotation in _assignments(inner):
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == positional[0].arg
                    ):
                        _settle(attributes, target.attr, self._type_of(value, annotation))
            self.scopes.pop()
        self.attributes[symbol] = {name: kind for name, kind in attributes.items() if kind}

        self.scopes.append({})
        for item in node.body:
            self.visit(item)
        self.scopes.pop()
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        defaults = [default for default in node.args.kw_defaults if default is not None]
        for outside in [*node.decorator_list, *node.args.defaults, *defaults]:
            self.visit(outside)
        self.scopes.append(self._types(node.body, node))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _wrote(self, node: ast.AST) -> bool:
        if self.lines is None:
            return True
        return any(start <= node.end_lineno and node.lineno < end for start, end in self.lines)

    def visit_Await(self, node: ast.Await) -> None:
        if isinstance(node.value, ast.Call):
            self.awaited[id(node.value)] = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        symbol = self.symbol_of(node.func)
        if symbol and self._wrote(node):
            self.found.append(
                Call(
                    symbol=self.resolve(symbol),
                    file=self.path,
                    line=node.lineno,
                    code=ast.unparse(node),
                    positional=sum(not isinstance(arg, ast.Starred) for arg in node.args),
                    keywords=tuple(keyword.arg for keyword in node.keywords if keyword.arg),
                    open_ended=any(isinstance(arg, ast.Starred) for arg in node.args)
                    or any(keyword.arg is None for keyword in node.keywords),
                    awaited=self.awaited.get(id(node), False),
                )
            )
        # asyncio.run(f()) or gather(f()) awaits f() for us, so it's not a plain call.
        for value in [*node.args, *(keyword.value for keyword in node.keywords)]:
            if isinstance(value, ast.Call):
                self.awaited.setdefault(id(value), None)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not self._wrote(node):
            return
        base = _from_base(node, self.path.removeprefix("src/").split("/")[:-1])
        for alias in node.names:
            if alias.name != "*":
                symbol = self.resolve(f"{base}.{alias.name}")
                self.imported.append(
                    Call(symbol, self.path, node.lineno, ast.unparse(node), 0, (), True, None, "import")
                )


def _is_none(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def calls(
    source: str,
    path: str,
    resolve: Callable[[str], str] | None = None,
    lines: list[list[int]] | None = None,
) -> list[Call]:
    """Every call whose target can be named, then every name imported from a module.

    Imports come last, so a call to a vanished name is reported at the call itself.
    `lines` keeps only what sits on those [start, end) lines: the ones this work wrote.
    A call nobody touched is already on main, where whoever changes the function sees it.
    """
    tree = _parse(source)
    finder = _Calls(tree, path, resolve or (lambda symbol: symbol), lines)
    finder.visit(tree)
    return [*finder.found, *finder.imported]


def problem(
    signature: Signature | None, call: Call, before: Signature | None = None
) -> str | None:
    """Why this call breaks against this signature, or None if it still fits.

    `before` is the signature the call was written against, when it changed.
    """
    if signature is None:
        return f"{'imports' if call.kind == 'import' else 'calls'} a name that no longer exists"
    if call.kind == "import":
        return None

    accepted = set(signature.positional) | set(signature.keyword_only)
    if not signature.varkw:
        unknown = [name for name in call.keywords if name not in accepted]
        if unknown:
            return f"passes unknown keyword {unknown[0]}"
    if not signature.varargs and call.positional > len(signature.positional):
        return (
            f"passes {call.positional} positional arguments, "
            f"the function takes {len(signature.positional)}"
        )
    if before is not None:
        if signature.is_async and not before.is_async and call.awaited is False:
            return "calls it without await, and it's async now"
        if before.is_async and not signature.is_async and call.awaited is True:
            return "awaits it, and it isn't async any more"
        shared = min(call.positional, len(before.positional), len(signature.positional))
        for index in range(shared):
            old, new = before.positional[index], signature.positional[index]
            if old != new and old in signature.positional:
                return f"passes {old} as argument {index + 1}, and that's {new} now"
    if call.open_ended:
        return None

    filled = set(signature.positional[: call.positional]) | set(call.keywords)
    missing = [name for name in signature.required if name not in filled]
    return f"is missing required argument {missing[0]}" if missing else None


def signature_from(data: dict[str, Any] | None) -> Signature | None:
    if data is None:
        return None
    lists = ("positional", "keyword_only", "required")
    return Signature(**{**data, **{key: tuple(data[key]) for key in lists}})


def call_from(data: dict[str, Any]) -> Call:
    return Call(**{**data, "keywords": tuple(data["keywords"])})


def changes(before: str, after: str, path: str) -> list[dict[str, Any]]:
    """Definitions this edit changed, removed or added, as JSON-ready records."""
    module = module_name(path)
    old = definitions(before, module)
    new = definitions(after, module)

    records = []
    for symbol in sorted(old.keys() | new.keys()):
        was, now = old.get(symbol), new.get(symbol)
        if was and now and was.fingerprint == now.fingerprint:
            continue
        records.append(
            {
                "symbol": symbol,
                "file": path,
                "before": asdict(was.signature) if was else None,
                "after": asdict(now.signature) if now else None,
                # The same edit on two laptops shows up as the same fingerprint.
                "fingerprint": now.fingerprint if now else None,
                # Where it sat in the base file, to name a line clash after it.
                "lines": list(was.lines) if was else None,
            }
        )
    return records
