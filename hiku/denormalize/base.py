from collections import deque
from typing import (
    Deque,
    Dict,
)

from ..graph import Graph
from ..query import (
    QueryVisitor,
    Link,
    Field,
    Node,
)
from ..result import Proxy
from ..types import (
    TypeRefMeta,
    OptionalMeta,
    SequenceMeta,
    get_type,
    RecordMeta,
)


class Denormalize(QueryVisitor):

    def __init__(
        self,
        graph: Graph,
        result: Proxy
    ) -> None:
        self._types = graph.__types__
        self._result = result
        self._type: Deque[RecordMeta] = deque([self._types['__root__']])
        self._data = deque([result])
        self._res: Deque = deque()

    def process(self, query: Node) -> Dict:
        assert not self._res, self._res
        self._res.append({})
        self.visit(query)
        return self._res.pop()

    def visit_field(self, obj: Field) -> None:
        self._res[-1][obj.result_key] = self._data[-1][obj.result_key]

    def visit_link(self, obj: Link) -> None:
        type_ = self._type[-1].__field_types__[obj.name]
        if isinstance(type_, TypeRefMeta):
            self._type.append(get_type(self._types, type_))
            self._res.append({})
            self._data.append(self._data[-1][obj.result_key])
            super().visit_link(obj)
            self._data.pop()
            self._res[-1][obj.result_key] = self._res.pop()
            self._type.pop()
        elif isinstance(type_, SequenceMeta):
            assert isinstance(type_.__item_type__, TypeRefMeta)
            self._type.append(get_type(self._types, type_.__item_type__))
            items = []
            for item in self._data[-1][obj.result_key]:
                self._res.append({})
                self._data.append(item)
                super().visit_link(obj)
                self._data.pop()
                items.append(self._res.pop())
            self._res[-1][obj.result_key] = items
            self._type.pop()
        elif isinstance(type_, OptionalMeta):
            if self._data[-1][obj.result_key] is None:
                self._res[-1][obj.result_key] = None
            else:
                assert isinstance(type_.__type__, TypeRefMeta)
                self._type.append(get_type(self._types, type_.__type__))
                self._res.append({})
                self._data.append(self._data[-1][obj.result_key])
                super().visit_link(obj)
                self._data.pop()
                self._res[-1][obj.result_key] = self._res.pop()
                self._type.pop()
        else:
            raise AssertionError(repr(type_))
