import typing as t

from abc import abstractmethod, ABC
from collections import OrderedDict


class GenericMeta(type):

    def __repr__(cls) -> str:
        return cls.__name__

    def __eq__(cls, other: t.Any) -> bool:
        return (cls.__class__ is other.__class__
                and cls.__dict__ == other.__dict__)

    def __ne__(cls, other: t.Any) -> bool:
        return not cls.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.__name__)

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        raise NotImplementedError(type(cls))


class AnyMeta(GenericMeta):

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_any(cls)


class Any(metaclass=AnyMeta):
    pass


class BooleanMeta(GenericMeta):

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_boolean(cls)


class Boolean(metaclass=BooleanMeta):
    pass


class StringMeta(GenericMeta):

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_string(cls)


class String(metaclass=StringMeta):
    pass


class IntegerMeta(GenericMeta):

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_integer(cls)


class Integer(metaclass=IntegerMeta):
    pass


class FloatMeta(GenericMeta):

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_float(cls)


class Float(metaclass=FloatMeta):
    pass


TM = t.TypeVar('TM', bound='TypingMeta')


class TypingMeta(GenericMeta, type):
    __final__ = False

    def __cls_init__(cls: TM, parameters: t.Any) -> None:
        raise NotImplementedError(type(cls))

    def __cls_repr__(cls: TM) -> str:
        raise NotImplementedError(type(cls))

    def __getitem__(cls: TM, parameters: t.Any) -> TM:
        if cls.__final__:
            raise TypeError('Cannot substitute parameters in {!r}'.format(cls))
        type_ = cls.__class__(cls.__name__, cls.__bases__, dict(cls.__dict__))
        type_.__cls_init__(parameters)
        type_.__final__ = True
        return type_

    def __repr__(self) -> str:
        if self.__final__:
            return self.__cls_repr__()
        else:
            return super(TypingMeta, self).__repr__()

    def __hash__(self) -> int:
        return hash(self.__name__)


class OptionalMeta(TypingMeta):
    __type__: GenericMeta

    def __cls_init__(cls, type_: GenericMeta) -> None:
        cls.__type__: GenericMeta = _maybe_typeref(type_)

    def __cls_repr__(self) -> str:
        return '{}[{!r}]'.format(self.__name__, self.__type__)

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_optional(cls)


class Optional(metaclass=OptionalMeta):
    pass


class SequenceMeta(TypingMeta):
    __item_type__: GenericMeta

    def __cls_init__(cls, item_type: GenericMeta) -> None:
        cls.__item_type__: GenericMeta = _maybe_typeref(item_type)

    def __cls_repr__(self) -> str:
        return '{}[{!r}]'.format(self.__name__, self.__item_type__)

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_sequence(cls)


class Sequence(metaclass=SequenceMeta):
    pass


class MappingMeta(TypingMeta):
    __key_type__: GenericMeta
    __value_type__: GenericMeta

    def __cls_init__(cls, params: t.Tuple[GenericMeta, GenericMeta]) -> None:
        key_type, value_type = params
        cls.__key_type__ = _maybe_typeref(key_type)
        cls.__value_type__ = _maybe_typeref(value_type)

    def __cls_repr__(self) -> str:
        return '{}[{!r}, {!r}]'.format(self.__name__, self.__key_type__,
                                       self.__value_type__)

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_mapping(cls)


class Mapping(metaclass=MappingMeta):
    pass


class RecordMeta(TypingMeta):
    __field_types__: OrderedDict

    def __cls_init__(
        cls,
        field_types: t.Union[
            t.Dict[str, GenericMeta],
            t.List[t.Tuple[str, GenericMeta]]
        ]
    ) -> None:
        items: t.Iterable
        if hasattr(field_types, 'items'):
            field_types = t.cast(t.Dict[str, GenericMeta], field_types)
            items = list(field_types.items())
        else:
            items = list(field_types)
        cls.__field_types__ = OrderedDict(
            (key, _maybe_typeref(val)) for key, val in items
        )

    def __cls_repr__(self) -> str:
        return '{}[{!r}]'.format(self.__name__, dict(self.__field_types__))

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_record(cls)


class Record(metaclass=RecordMeta):
    __field_types__: OrderedDict


class CallableMeta(TypingMeta):

    def __cls_init__(cls, arg_types: t.Iterable[GenericMeta]) -> None:
        cls.__arg_types__ = [_maybe_typeref(typ) for typ in arg_types]

    def __cls_repr__(self) -> str:
        return '{}[{}]'.format(self.__name__,
                               ', '.join(map(repr, self.__arg_types__)))

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_callable(cls)


class Callable(metaclass=CallableMeta):
    pass


class TypeRefMeta(TypingMeta):
    __type_name__: str

    def __cls_init__(cls, *args: str) -> None:
        assert len(args) == 1, f'{cls.__name__} takes exactly one argument'

        cls.__type_name__ = args[0]

    def __cls_repr__(self) -> str:
        return '{}[{!r}]'.format(self.__name__, self.__type_name__)

    def accept(cls, visitor: 'AbstractTypeVisitor') -> t.Any:
        return visitor.visit_typeref(cls)


class TypeRef(metaclass=TypeRefMeta):
    ...


@t.overload
def _maybe_typeref(typ: str) -> TypeRefMeta:
    ...


@t.overload
def _maybe_typeref(typ: GenericMeta) -> GenericMeta:
    ...


def _maybe_typeref(typ: t.Union[str, GenericMeta]) -> GenericMeta:
    return TypeRef[typ] if isinstance(typ, str) else typ


class AbstractTypeVisitor(ABC):

    def visit(self, obj: GenericMeta) -> t.Any:
        return obj.accept(self)

    @abstractmethod
    def visit_any(self, obj: AnyMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_boolean(self, obj: BooleanMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_string(self, obj: StringMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_integer(self, obj: IntegerMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_float(self, obj: FloatMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_typeref(self, obj: TypeRefMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_optional(self, obj: OptionalMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_sequence(self, obj: SequenceMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_mapping(self, obj: MappingMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_record(self, obj: RecordMeta) -> t.Any:
        pass

    @abstractmethod
    def visit_callable(self, obj: CallableMeta) -> t.Any:
        pass


class TypeVisitor(AbstractTypeVisitor):

    def visit_any(self, obj: AnyMeta) -> t.Any:
        pass

    def visit_boolean(self, obj: BooleanMeta) -> t.Any:
        pass

    def visit_string(self, obj: StringMeta) -> t.Any:
        pass

    def visit_integer(self, obj: IntegerMeta) -> t.Any:
        pass

    def visit_float(self, obj: FloatMeta) -> t.Any:
        pass

    def visit_typeref(self, obj: TypeRefMeta) -> t.Any:
        pass

    def visit_optional(self, obj: OptionalMeta) -> t.Any:
        self.visit(obj.__type__)

    def visit_sequence(self, obj: SequenceMeta) -> t.Any:
        self.visit(obj.__item_type__)

    def visit_mapping(self, obj: MappingMeta) -> t.Any:
        self.visit(obj.__key_type__)
        self.visit(obj.__value_type__)

    def visit_record(self, obj: RecordMeta) -> t.Any:
        for value_type in obj.__field_types__.values():
            self.visit(value_type)

    def visit_callable(self, obj: CallableMeta) -> t.Any:
        for arg_type in obj.__arg_types__:
            self.visit(arg_type)


@t.overload
def get_type(
    types: t.Dict[str, t.Type[Record]], typ: TypeRefMeta
) -> t.Type[Record]:
    ...


@t.overload
def get_type(
    types: t.Dict[str, t.Type[Record]], typ: GenericMeta
) -> GenericMeta:
    ...


@t.overload
def get_type(
    types: t.Dict[str, t.Type[Record]], typ: t.Optional[GenericMeta]
) -> t.Optional[GenericMeta]:
    ...


def get_type(types, typ):  # type: ignore[no-untyped-def]
    if isinstance(typ, TypeRefMeta):
        return types[typ.__type_name__]
    else:
        return typ
