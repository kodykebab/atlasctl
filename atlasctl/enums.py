"""Turn a generated string enum into the choices a click.Choice option needs."""

from __future__ import annotations

from enum import Enum


def enum_choices(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
