from unittest.mock import ANY

import pytest

from hiku.directives import Deprecated
from hiku.graph import Graph, Root, Field, Node, Link, apply, Option
from hiku.types import String, Integer, Sequence, TypeRef, Boolean, Float, Any
from hiku.types import Optional, Record
from hiku.result import denormalize
from hiku.engine import Engine
from hiku.executors.sync import SyncExecutor
from hiku.validate.query import validate
from hiku.readers.graphql import read
from hiku.introspection.graphql import GraphQLIntrospection
from tests.utils import INTROSPECTION_QUERY


def _noop():
    raise NotImplementedError


def _non_null(t):
    return {'kind': 'NON_NULL', 'name': None, 'ofType': t}


_INT = {'kind': 'SCALAR', 'name': 'Int', 'ofType': None}
_STR = {'kind': 'SCALAR', 'name': 'String', 'ofType': None}
_BOOL = {'kind': 'SCALAR', 'name': 'Boolean', 'ofType': None}
_FLOAT = {'kind': 'SCALAR', 'name': 'Float', 'ofType': None}
_ANY = {'kind': 'SCALAR', 'name': 'Any', 'ofType': None}


def _obj(name):
    return {'kind': 'OBJECT', 'name': name, 'ofType': None}


def _iobj(name):
    return {'kind': 'INPUT_OBJECT', 'name': name, 'ofType': None}


def _seq_of(_type):
    return {'kind': 'NON_NULL', 'name': None,
            'ofType': {'kind': 'LIST', 'name': None,
                       'ofType': {'kind': 'NON_NULL', 'name': None,
                                  'ofType': _type}}}


def _field(name, type_, **kwargs):
    data = {
        'args': [],
        'deprecationReason': None,
        'description': None,
        'isDeprecated': False,
        'name': name,
        'type': type_
    }
    data.update(kwargs)
    return data


def _type(name, kind, **kwargs):
    data = {
        'description': None,
        'enumValues': [],
        'fields': [],
        'inputFields': [],
        'interfaces': [],
        'kind': kind,
        'name': name,
        'possibleTypes': [],
    }
    data.update(**kwargs)
    return data


def _directive(name, args):
    return {
        'name': name,
        'description': ANY,
        "locations": ["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
        "args": args,
    }


def _field_enum_directive(name, args):
    return {
        'name': name,
        'description': ANY,
        'locations': ['FIELD_DEFINITION', 'ENUM_VALUE'],
        'args': args,
    }


def _schema(types, with_mutation=False):
    names = [t['name'] for t in types]
    assert 'Query' in names, names
    return {
        '__schema': {
            'directives': [
                _directive('skip', [
                    _ival('if', _non_null(_BOOL), description=ANY),
                ]),
                _directive('include', [
                    _ival('if', _non_null(_BOOL), description=ANY),
                ]),
                _field_enum_directive('deprecated', [
                    _ival('reason', _STR, description=ANY)
                ]),
                _directive('cached', [
                    _ival('ttl', _non_null(_INT), description=ANY),
                ]),
            ],
            'mutationType': {'name': 'Mutation'} if with_mutation else None,
            'queryType': {'name': 'Query'},
            'types': SCALARS + types,
        }
    }


def _ival(name, type_, **kwargs):
    data = {
        'name': name,
        'type': type_,
        'description': None,
        'defaultValue': None,
    }
    data.update(kwargs)
    return data


SCALARS = [
    _type('String', 'SCALAR'),
    _type('Int', 'SCALAR'),
    _type('Boolean', 'SCALAR'),
    _type('Float', 'SCALAR'),
    _type('Any', 'SCALAR'),
]


def introspect(query_graph, mutation_graph=None):
    engine = Engine(SyncExecutor())
    query_graph = apply(query_graph, [
        GraphQLIntrospection(query_graph, mutation_graph),
    ])

    query = read(INTROSPECTION_QUERY)
    errors = validate(query_graph, query)
    assert not errors

    norm_result = engine.execute(query_graph, query)
    return denormalize(query_graph, norm_result)


def test_introspection_query():
    graph = Graph([
        Node('flexed', [
            Field('yari', Boolean, _noop, options=[
                Option('membuka', Sequence[String], default=['frayed']),
                Option('modist', Optional[Integer], default=None,
                       description='callow'),
            ]),
        ]),
        Node('decian', [
            Field('dogme', Integer, _noop),
            Link('clarkia', Sequence[TypeRef['flexed']], _noop, requires=None),
        ]),
        Root([
            Field('_cowered', String, _noop),
            Field('entero', Float, _noop),
            Field('oldField', Float, _noop,
                  directives=[Deprecated('obsolete')]),
            Link('oldLink', Sequence[TypeRef['decian']], _noop, requires=None,
                 directives=[Deprecated('obsolete link')]),
            Link('toma', Sequence[TypeRef['decian']], _noop, requires=None),
        ]),
    ])
    assert introspect(graph) == _schema([
        _type('flexed', 'OBJECT', fields=[
            _field('yari', _non_null(_BOOL), args=[
                _ival('membuka', _seq_of(_STR), defaultValue='["frayed"]'),
                _ival('modist', _INT, defaultValue='null',
                      description='callow'),
            ]),
        ]),
        _type('decian', 'OBJECT', fields=[
            _field('dogme', _non_null(_INT)),
            _field('clarkia', _seq_of(_obj('flexed'))),
        ]),
        _type('Query', 'OBJECT', fields=[
            _field('entero', _non_null(_FLOAT)),
            _field(
                'oldField',
                _non_null(_FLOAT),
                isDeprecated=True,
                deprecationReason='obsolete',
            ),
            _field(
                'oldLink',
                _seq_of(_obj('decian')),
                isDeprecated=True,
                deprecationReason='obsolete link',
            ),
            _field('toma', _seq_of(_obj('decian'))),
        ]),
    ])


def test_invalid_names():
    graph = Graph([
        Node('Baz-Baz', [
            Field('bzz-bzz', Integer, _noop),
        ]),
        Root([
            Field('foo-foo', Integer, _noop,
                  options=[Option('bar-bar', Integer)]),
            Link('baz-baz', Sequence[TypeRef['Baz-Baz']], _noop,
                 requires='foo-foo'),
        ]),
    ])
    with pytest.raises(ValueError) as err:
        apply(graph, [GraphQLIntrospection(graph)])
    assert err.match('bzz-bzz')
    assert err.match('foo-foo')
    assert err.match('bar-bar')
    assert err.match('baz-baz')
    assert err.match('Baz-Baz')


def test_empty_nodes():
    graph = Graph([
        Node('Foo', []),
        Root([]),
    ])
    with pytest.raises(ValueError) as err:
        apply(graph, [GraphQLIntrospection(graph)])
    assert err.match('No fields in the Foo node')
    assert err.match('No fields in the Root node')


def test_unsupported_field_type():
    graph = Graph([
        Root([
            Field('fall', Optional[Any], _noop),
            Field('bayman', Optional[Record[{'foo': Optional[Integer]}]],
                  _noop),
            Field('huss', Integer, _noop),
        ]),
    ])
    assert introspect(graph) == _schema([
        _type('Query', 'OBJECT', fields=[
            _field('fall', _ANY),
            _field('bayman', _ANY),
            _field('huss', _non_null(_INT)),
        ]),
    ])


def test_unsupported_option_type():
    graph = Graph([
        Root([
            Field('huke', Integer, _noop,
                  options=[Option('orel', Optional[Any])]),
            Field('terapin', Integer, _noop),
        ]),
    ])
    assert introspect(graph) == _schema([
        _type('Query', 'OBJECT', fields=[
            _field('huke', _non_null(_INT), args=[
                _ival('orel', _ANY),
            ]),
            _field('terapin', _non_null(_INT)),
        ]),
    ])


def test_data_types():
    data_types = {
        'Foo': Record[{
            'bar': Integer,
        }],
    }
    graph = Graph([Root([
        Field('foo', TypeRef['Foo'], _noop),
    ])], data_types)
    assert introspect(graph) == _schema([
        _type('Query', 'OBJECT', fields=[
            _field('foo', _non_null(_obj('Foo'))),
        ]),
        _type('Foo', 'OBJECT', fields=[
            _field('bar', _non_null(_INT)),
        ]),
        _type('IOFoo', 'INPUT_OBJECT', inputFields=[
            _ival('bar', _non_null(_INT)),
        ]),
    ])


def test_mutation_type():
    data_types = {
        'Foo': Record[{
            'bar': Integer,
        }],
    }
    query_graph = Graph([Root([
        Field('getFoo', Integer, _noop, options=[
            Option('getterArg', TypeRef['Foo']),
        ]),
    ])], data_types)
    mutation_graph = Graph(query_graph.nodes + [Root([
        Field('setFoo', Integer, _noop, options=[
            Option('setterArg', TypeRef['Foo']),
        ]),
    ])], data_types=query_graph.data_types)
    assert introspect(query_graph, mutation_graph) == _schema([
        _type('Query', 'OBJECT', fields=[
            _field('getFoo', _non_null(_INT), args=[
                _ival('getterArg', _non_null(_iobj('IOFoo'))),
            ]),
        ]),
        _type('Mutation', 'OBJECT', fields=[
            _field('setFoo', _non_null(_INT), args=[
                _ival('setterArg', _non_null(_iobj('IOFoo'))),
            ]),
        ]),
        _type('Foo', 'OBJECT', fields=[
            _field('bar', _non_null(_INT)),
        ]),
        _type('IOFoo', 'INPUT_OBJECT', inputFields=[
            _ival('bar', _non_null(_INT)),
        ]),
    ], with_mutation=True)


def test_untyped_fields():
    graph = Graph([
        Root([
            Field('untyped', None, _noop),
            Field('any_typed', Any, _noop),
        ]),
    ])
    assert introspect(graph) == _schema([
        _type('Query', 'OBJECT', fields=[
            _field('untyped', _ANY),
            _field('any_typed', _ANY),
        ]),
    ])
