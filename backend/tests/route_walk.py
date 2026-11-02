"""List every route an app serves, across FastAPI versions.

FastAPI <= 0.136 flattens included routers into ``app.routes``. Newer releases
(seen on 0.162) keep one lazy ``_IncludedRouter`` entry per ``include_router``
call instead, so a flat scan of ``app.routes`` misses the included routes. This
walk descends into both shapes (and into Starlette ``Mount``s) and joins prefixes.
"""
from __future__ import annotations

from collections.abc import Iterator

from starlette.routing import BaseRoute, Mount, WebSocketRoute


def iter_routes(routes: list[BaseRoute], prefix: str = "") -> Iterator[tuple[str, BaseRoute]]:
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:  # FastAPI >= 0.16x include_router entry
            context = getattr(route, "include_context", None)
            yield from iter_routes(included.routes, prefix + getattr(context, "prefix", ""))
        elif isinstance(route, Mount):
            yield from iter_routes(route.routes, prefix + route.path)
        else:
            yield prefix + getattr(route, "path", ""), route


def route_paths(app) -> set[str]:
    return {path for path, _ in iter_routes(app.routes)}


def websocket_paths(app) -> set[str]:
    return {path for path, route in iter_routes(app.routes) if isinstance(route, WebSocketRoute)}
