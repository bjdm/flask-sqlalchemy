from __future__ import annotations

import re
import typing as t

import sqlalchemy as sa
import sqlalchemy.orm

if t.TYPE_CHECKING:
    from .extension import SQLAlchemy


class Base(sa.orm.DeclarativeBase):
    __fsa__: t.ClassVar[SQLAlchemy]
    """Internal reference to the extension object.

    :meta private:
    """

    def __repr__(self) -> str:
        state = sa.inspect(self)

        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(map(str, state.identity))

        return f"<{type(self).__name__} {pk}>"


class NameMixin:
    """Mixin to add a snake-cased table name to models.

    Will add a snake-cased table name to any DeclarativeBase models that do not provide
    one in its own implementation, or that of a parent class. It will also not add a
    table name if it is an abstract model or is a single-table inheritance.
    """

    # TODO: Is this the correct method signature?
    @sa.orm.declared_attr
    def __tablename__(cls) -> str | None:  # noqa: B902
        """Override SQLAlchemy built-in method."""
        # determine whether a primar key has been declared
        if hasattr(cls, "id") and getattr(cls.id, "primary_key", False):
            return camel_to_snake_case(cls.__name__)
        else:
            return None


def should_set_tablename(cls: NameMixin) -> bool:
    """Determine whether ``__tablename__`` should be generated for a model.

    -   If no class in the MRO sets a name, one should be generated.
    -   If a declared attr is found, it should be used instead.
    -   If a name is found, it should be used if the class is a mixin, otherwise one
        should be generated.
    -   Abstract models should not have one generated.

    Later, ``__table_cls__`` will determine if the model looks like single or
    joined-table inheritance. If no primary key is found, the name will be unset.
    """
    if cls.__dict__.get("__abstract__", False) or not any(
        isinstance(b, sa.orm.DeclarativeMeta) for b in cls.__mro__[1:]
    ):
        return False

    for base in cls.__mro__:
        if "__tablename__" not in base.__dict__:
            continue

        if isinstance(base.__dict__["__tablename__"], sa.orm.declared_attr):
            return False

        return not (
            base is cls
            or base.__dict__.get("__abstract__", False)
            or not isinstance(base, sa.orm.DeclarativeMeta)
        )

    return True


def camel_to_snake_case(name: str) -> str:
    """Convert a ``CamelCase`` name to ``snake_case``."""
    name = re.sub(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))", r"_\1", name)
    return name.lower().lstrip("_")
