from ..types import Any as Any, AnyMeta as AnyMeta, MappingMeta as MappingMeta, OptionalMeta as OptionalMeta, Record as Record, RecordMeta as RecordMeta, Sequence as Sequence, SequenceMeta as SequenceMeta, get_type as get_type
from .nodes import Keyword as Keyword, List as List, NodeTransformer as NodeTransformer, Symbol as Symbol, Tuple as Tuple
from .refs import NamedRef as NamedRef, Ref as Ref
from _typeshed import Incomplete
from collections.abc import Generator

def fn_types(functions): ...

class Environ:
    vars: Incomplete
    def __init__(self, values) -> None: ...
    def push(self, mapping) -> Generator[None, None, None]: ...
    def __getitem__(self, key): ...
    def __contains__(self, key): ...

def node_type(types, node): ...
def check_type(types, t1, t2) -> None: ...

class Checker(NodeTransformer):
    types: Incomplete
    env: Incomplete
    def __init__(self, types, env) -> None: ...
    def visit_get_expr(self, node): ...
    def visit_each_expr(self, node): ...
    def visit_if_some_expr(self, node): ...
    def visit_tuple_generic(self, node): ...
    def visit_tuple(self, node): ...
    def visit_symbol(self, node): ...
    def visit_dict(self, node): ...

def check(expr, types, env): ...
