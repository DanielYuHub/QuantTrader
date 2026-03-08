"""Minimal local compatibility shim for required Pydantic v2 APIs.

This module is intentionally small and supports only the API surface used by this
repository's tests in environments where the real `pydantic` package is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class _MissingType:
    pass


_MISSING = _MissingType()


@dataclass(frozen=True)
class FieldInfo:
    """Field metadata and default settings."""

    default: Any = _MISSING
    default_factory: Callable[[], Any] | None = None
    ge: float | None = None
    gt: float | None = None
    le: float | None = None


def Field(  # noqa: N802 - match pydantic API naming
    default: Any = _MISSING,
    *,
    default_factory: Callable[[], Any] | None = None,
    ge: float | None = None,
    gt: float | None = None,
    le: float | None = None,
    description: str | None = None,
) -> FieldInfo:
    """Return lightweight field metadata."""

    _ = description
    return FieldInfo(default=default, default_factory=default_factory, ge=ge, gt=gt, le=le)


PositiveInt = int


def model_validator(*, mode: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register model-level validator function."""

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_model_validator_mode", mode)
        return func

    return _decorator


class BaseModel:
    """Very small BaseModel subset with init/copy/validation behavior."""

    __field_defs__: dict[str, FieldInfo]
    __model_validators__: list[str]

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.__field_defs__ = {}
        annotations = getattr(cls, "__annotations__", {})
        for name in annotations:
            raw_default = getattr(cls, name, _MISSING)
            if isinstance(raw_default, FieldInfo):
                field_info = raw_default
            elif raw_default is _MISSING:
                field_info = FieldInfo(default=_MISSING)
            else:
                field_info = FieldInfo(default=raw_default)
            cls.__field_defs__[name] = field_info

        cls.__model_validators__ = []
        for name, value in cls.__dict__.items():
            if callable(value) and getattr(value, "_model_validator_mode", None) == "after":
                cls.__model_validators__.append(name)

    def __init__(self, **data: Any) -> None:
        annotations = getattr(self.__class__, "__annotations__", {})
        for name, annotation in annotations.items():
            field_info = self.__class__.__field_defs__.get(name, FieldInfo(default=_MISSING))
            if name in data:
                value = data[name]
            elif field_info.default_factory is not None:
                value = field_info.default_factory()
            elif field_info.default is not _MISSING:
                value = field_info.default
            else:
                msg = f"Missing required field: {name}"
                raise TypeError(msg)

            self._validate_field(name, annotation, value, field_info)
            setattr(self, name, value)

        for validator_name in getattr(self.__class__, "__model_validators__", []):
            result = getattr(self, validator_name)()
            if result is not self:
                msg = f"Model validator '{validator_name}' must return self"
                raise ValueError(msg)

    def model_copy(self, *, update: dict[str, Any] | None = None) -> "BaseModel":
        """Return copied model with optional field updates."""

        payload = self.model_dump()
        if update:
            payload.update(update)
        return self.__class__(**payload)

    def model_dump(self) -> dict[str, Any]:
        """Return model data as a dictionary."""

        return {name: getattr(self, name) for name in getattr(self.__class__, "__annotations__", {})}

    @staticmethod
    def _validate_field(name: str, annotation: Any, value: Any, field_info: FieldInfo) -> None:
        if value is None:
            return

        if annotation is PositiveInt:
            if not isinstance(value, int) or value <= 0:
                msg = f"Field '{name}' must be a positive integer"
                raise ValueError(msg)

        if field_info.ge is not None and value < field_info.ge:
            msg = f"Field '{name}' must be >= {field_info.ge}"
            raise ValueError(msg)
        if field_info.gt is not None and value <= field_info.gt:
            msg = f"Field '{name}' must be > {field_info.gt}"
            raise ValueError(msg)
        if field_info.le is not None and value > field_info.le:
            msg = f"Field '{name}' must be <= {field_info.le}"
            raise ValueError(msg)
