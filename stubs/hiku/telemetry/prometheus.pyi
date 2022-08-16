import abc
from ..engine import pass_context as pass_context
from ..graph import GraphTransformer as GraphTransformer
from ..sources.graph import CheckedExpr as CheckedExpr
from _typeshed import Incomplete
from abc import abstractmethod

class GraphMetricsBase(GraphTransformer, metaclass=abc.ABCMeta):
    root_name: str
    def __init__(self, name, *, metric: Incomplete | None = ...) -> None: ...
    @abstractmethod
    def field_wrapper(self, observe, func): ...
    @abstractmethod
    def link_wrapper(self, observe, func): ...
    @abstractmethod
    def subquery_wrapper(self, observe, subquery): ...
    def visit_node(self, obj): ...
    def visit_field(self, obj): ...
    def visit_link(self, obj): ...

class _SubqueryMixin:
    def subquery_wrapper(self, observe, subquery): ...

class GraphMetrics(_SubqueryMixin, GraphMetricsBase):
    def field_wrapper(self, observe, func): ...
    def link_wrapper(self, observe, func): ...

class AsyncGraphMetrics(_SubqueryMixin, GraphMetricsBase):
    def field_wrapper(self, observe, func): ...
    def link_wrapper(self, observe, func): ...
