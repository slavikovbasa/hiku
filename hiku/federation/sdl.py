import typing as t

from math import isfinite
from typing import (
    Optional,
    Iterable,
    List,
)

from graphql.language.printer import print_ast
from graphql.language import ast
from graphql.pyutils import inspect

from hiku.directives import Deprecated
from hiku.federation.directive import (
    Extends,
    External,
    Requires,
    Provides,
    Key,
)
from hiku.graph import (
    Link,
    Nothing,
    GraphVisitor,
    Field,
    Node,
    Root,
    GraphTransformer,
    Graph,
    Option,
)
from hiku.types import (
    IntegerMeta,
    TypeRefMeta,
    StringMeta,
    SequenceMeta,
    OptionalMeta,
    AnyMeta,
    FloatMeta,
    BooleanMeta,
    Record,
    GenericMeta,
)


def _name(value: t.Optional[str]) -> t.Optional[ast.NameNode]:
    return ast.NameNode(value=value) if value is not None else None


@t.overload
def coerce_type(x: str) -> ast.NameNode: ...


@t.overload
def coerce_type(x: ast.Node) -> ast.Node: ...


def coerce_type(x):  # type: ignore[no-untyped-def]
    if isinstance(x, str):
        return _name(x)
    return x


def _non_null_type(val: t.Union[str, ast.Node]) -> ast.NonNullTypeNode:
    return ast.NonNullTypeNode(type=coerce_type(val))


def _encode_type(value: t.Any) -> t.Union[
    ast.NonNullTypeNode,
    ast.NameNode,
]:
    def _encode(
        val: t.Optional[GenericMeta]
    ) -> t.Union[str, t.Tuple, ast.ListTypeNode]:
        if isinstance(val, OptionalMeta):
            return _encode(val.__type__), True
        elif isinstance(val, TypeRefMeta):
            return val.__type_name__
        elif isinstance(val, IntegerMeta):
            return 'Int'
        elif isinstance(val, StringMeta):
            return 'String'
        elif isinstance(val, BooleanMeta):
            return 'Boolean'
        elif isinstance(val, SequenceMeta):
            return ast.ListTypeNode(type=_encode_type(val.__item_type__))
        elif isinstance(val, AnyMeta):
            return 'Any'
        elif isinstance(val, FloatMeta):
            return 'Float'
        elif val is None:
            return ''
        else:
            raise TypeError('Unsupported type: {!r}'.format(val))

    encoded = _encode(value)
    if isinstance(encoded, tuple):
        [type_, optional] = encoded
        if optional:
            return coerce_type(type_)
        return _non_null_type(type_)

    return _non_null_type(encoded)


def _encode_default_value(value: t.Any) -> Optional[ast.ValueNode]:
    if value == Nothing:
        return None

    if value is None:
        return ast.NullValueNode()

    if isinstance(value, bool):
        return ast.BooleanValueNode(value=value)

    if isinstance(value, int):
        return ast.IntValueNode(value=f"{value:d}")
    if isinstance(value, float) and isfinite(value):
        return ast.FloatValueNode(value=f"{value:g}")

    if isinstance(value, str):
        return ast.StringValueNode(value=value)

    if isinstance(value, Iterable) and not isinstance(value, str):
        maybe_value_nodes = (_encode_default_value(item) for item in value)
        value_nodes: t.List[ast.ValueNode] = list(
            filter(None, maybe_value_nodes)
        )
        return ast.ListValueNode(values=[value_nodes])

    raise TypeError(f"Cannot convert value to AST: {inspect(value)}.")


class Exporter(GraphVisitor):
    def export_record(
        self, type_name: str, obj: t.Type[Record]
    ) -> ast.ObjectTypeDefinitionNode:
        def new_field(name: str, type_: t.Any) -> ast.FieldDefinitionNode:
            return ast.FieldDefinitionNode(
                name=_name(name),
                type=_encode_type(type_),
            )
        fields = [new_field(f_name, field)
                  for f_name, field in obj.__field_types__.items()]
        return ast.ObjectTypeDefinitionNode(
            name=_name(type_name),
            fields=fields,
        )

    def visit_graph(self, obj: Graph) -> List[ast.DefinitionNode]:
        """List of ObjectTypeDefinitionNode and ObjectTypeExtensionNode"""
        return [
            self.get_any_type(),
            *[self.export_record(type_name, type_)
              for type_name, type_ in obj.data_types.items()],
            *[self.visit(item) for item in obj.items]
        ]

    def get_any_type(self) -> ast.ScalarTypeDefinitionNode:
        return ast.ScalarTypeDefinitionNode(name=_name('Any'))

    def visit_root(self, obj: Root) -> ast.ObjectTypeExtensionNode:
        return ast.ObjectTypeExtensionNode(
            name=_name('Query'),
            fields=[self.visit(item) for item in obj.fields],
        )

    def visit_field(self, obj: Field) -> ast.FieldDefinitionNode:
        return ast.FieldDefinitionNode(
            name=_name(obj.name),
            type=_encode_type(obj.type),
            arguments=[self.visit(o) for o in obj.options],
            directives=[self.visit(d) for d in obj.directives]
        )

    def visit_node(self, obj: Node) -> ast.ObjectTypeDefinitionNode:
        fields = [self.visit(field) for field in obj.fields]

        return ast.ObjectTypeDefinitionNode(
            name=_name(obj.name),
            fields=fields,
            directives=[self.visit(d) for d in obj.directives]
        )

    def visit_link(self, obj: Link) -> ast.FieldDefinitionNode:
        return ast.FieldDefinitionNode(
            name=_name(obj.name),
            arguments=[self.visit(o) for o in obj.options],
            type=_encode_type(obj.type),
            directives=[self.visit(d) for d in obj.directives]
        )

    def visit_option(self, obj: Option) -> ast.InputValueDefinitionNode:
        return ast.InputValueDefinitionNode(
            name=_name(obj.name),
            description=obj.description,
            type=_encode_type(obj.type),
            default_value=_encode_default_value(obj.default),
        )

    def visit_key_directive(self, obj: Key) -> ast.DirectiveNode:
        return ast.DirectiveNode(
            name=_name('key'),
            arguments=[
                ast.ArgumentNode(
                    name=_name('fields'),
                    value=ast.StringValueNode(value=obj.fields),
                ),
            ],
        )

    def visit_provides_directive(self, obj: Provides) -> ast.DirectiveNode:
        return ast.DirectiveNode(
            name=_name('provides'),
            arguments=[
                ast.ArgumentNode(
                    name=_name('fields'),
                    value=ast.StringValueNode(value=obj.fields),
                ),
            ],
        )

    def visit_requires_directive(self, obj: Requires) -> ast.DirectiveNode:
        return ast.DirectiveNode(
            name=_name('requires'),
            arguments=[
                ast.ArgumentNode(
                    name=_name('fields'),
                    value=ast.StringValueNode(value=obj.fields),
                ),
            ],
        )

    def visit_external_directive(self, obj: External) -> ast.DirectiveNode:
        return ast.DirectiveNode(name=_name('external'))

    def visit_extends_directive(self, obj: Extends) -> ast.DirectiveNode:
        return ast.DirectiveNode(name=_name('extends'))

    def visit_deprecated_directive(self, obj: Deprecated) -> ast.DirectiveNode:
        return ast.DirectiveNode(
            name=_name('deprecated'),
            arguments=[
                ast.ArgumentNode(
                    name=_name('reason'),
                    value=ast.StringValueNode(value=obj.reason),
                ),
            ],
        )


def get_ast(graph: Graph) -> ast.DocumentNode:
    graph = _StripGraph().visit(graph)
    return ast.DocumentNode(definitions=Exporter().visit(graph))


class _StripGraph(GraphTransformer):
    def visit_root(self, obj: Root) -> Root:
        def skip(field: t.Union[Field, Link]) -> bool:
            return field.name in ['__typename', '_entities']

        return Root([self.visit(f) for f in obj.fields if not skip(f)])

    def visit_graph(self, obj: Graph) -> Graph:
        def skip(node: Node) -> bool:
            if node.name is None:
                # check if it is a Root node from introspection
                return '__schema' in node.fields_map

            return node.name.startswith('__')

        return Graph(
            [self.visit(node) for node in obj.items if not skip(node)],
            obj.data_types
        )

    def visit_node(self, obj: Node) -> Node:
        def skip(field: t.Union[Field, Link]) -> bool:
            return field.name in ['__typename']

        return Node(
            obj.name,
            fields=[self.visit(f) for f in obj.fields if not skip(f)],
            description=obj.description,
            directives=obj.directives
        )


def print_sdl(graph: Graph) -> str:
    """Print graphql AST into a string"""
    return print_ast(get_ast(graph))
