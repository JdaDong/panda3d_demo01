"""课程注册表：``@register`` 装饰器 + 按 order 排序的查询。"""

from __future__ import annotations

from typing import TypeVar

from .lesson import Lesson

_REGISTRY: dict[str, type[Lesson]] = {}
L = TypeVar("L", bound=type[Lesson])


def register(cls: L) -> L:
    """类装饰器：把课程类加入注册表，并做基本合法性校验。"""
    if not cls.key:
        raise ValueError(f"{cls.__name__} must define a non-empty `key`")
    existing = _REGISTRY.get(cls.key)
    if existing is not None and existing is not cls:
        raise ValueError(f"duplicate lesson key: {cls.key}")
    if not cls.apis:
        raise ValueError(f"{cls.__name__} must list the Panda3D APIs it covers")
    _REGISTRY[cls.key] = cls
    return cls


def _ensure_loaded() -> None:
    # 导入 lessons 包会触发所有 @register（显式导入，顺序确定）
    from .. import lessons  # noqa: F401


def all_lessons() -> list[type[Lesson]]:
    _ensure_loaded()
    return sorted(_REGISTRY.values(), key=lambda c: (c.order, c.key))


def get_lesson(key: str) -> type[Lesson]:
    _ensure_loaded()
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"unknown lesson '{key}', choices: {sorted(_REGISTRY)}") from exc
