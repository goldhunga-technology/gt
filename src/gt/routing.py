from dataclasses import dataclass, fields
from typing import Self


@dataclass(slots=True, frozen=True, kw_only=True)
class RouteGroupConfig:
    """Base configuration for toggling individual endpoints within a router group."""

    default: bool = True

    def is_enabled(self, route: str) -> bool:
        """Return whether *route* is enabled, falling back to ``self.default``."""
        value = getattr(self, route)
        return self.default if value is None else value

    def any_enabled(self) -> bool:
        """Return True if at least one route in this group is enabled."""
        return any(
            self.is_enabled(field.name)
            for field in fields(self)
            if field.name != "default"
        )

    @classmethod
    def disabled(cls) -> Self:
        """Return a config with every route in this group disabled."""
        return cls(default=False)


@dataclass(slots=True, frozen=True, kw_only=True)
class ModuleRoutesConfig:
    """Base configuration for toggling router groups within a module."""

    default: bool = True

    @classmethod
    def disabled(cls) -> Self:
        """Return a config with every router group in this module disabled."""
        return cls(default=False)


def resolve_group[TGroup: RouteGroupConfig](
    value: bool | TGroup | None,
    *,
    default: bool,
    group_cls: type[TGroup],
) -> TGroup:
    """Resolve a module-level group toggle into a concrete ``RouteGroupConfig``."""
    if isinstance(value, group_cls):
        return value
    if value is None:
        return group_cls(default=default)
    if isinstance(value, bool):
        return group_cls(default=value)
    raise TypeError(
        f"Expected bool, {group_cls.__name__}, or None; got {type(value).__name__}"
    )


def resolve_module_routes[TConfig: ModuleRoutesConfig](
    routes: TConfig | bool | None,
    *,
    config_cls: type[TConfig],
) -> TConfig:
    """Normalize the ``routes`` argument passed to ``init_app``."""
    if routes is None or routes is True:
        return config_cls()
    if routes is False:
        return config_cls(default=False)
    if isinstance(routes, config_cls):
        return routes
    raise TypeError(
        f"Expected {config_cls.__name__}, bool, or None; got {type(routes).__name__}"
    )
