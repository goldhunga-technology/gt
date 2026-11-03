from __future__ import annotations

from collections.abc import Sequence

EndpointPath = str
EndpointMethod = str


class EndpointRule:
    """A single ``(method, path, required_role)`` entry describing a protected endpoint.

    Attributes
    ----------
    method: str
        Upper‑cased HTTP method (``"GET"``, ``"POST"``, etc.).
    path: str
        Route path as it appears in the router; may contain ``{param}`` wild‑cards.
    required_role: str | None
        Role name that must be held by the administrator. ``None`` means the
        endpoint is open (no role check).
    """

    __slots__ = ("method", "path", "required_role")

    def __init__(
        self,
        method: EndpointMethod,
        path: EndpointPath,
        required_role: str | None = None,
    ) -> None:
        self.method = method.upper()
        self.path = path
        self.required_role = required_role

    def __repr__(self) -> str:
        return f"EndpointRule(method={self.method!r}, path={self.path!r}, role={self.required_role!r})"


class AdminPolicy:
    r"""Holds a collection of :class:`EndpointRule`\ s and can match a request
    against them.

    The matching algorithm compares the HTTP method and then performs a
    segment‑wise comparison of the path.  A ``{param}`` placeholder in the
    rule pattern matches any single path segment.

    Attributes
    ----------
    rules: tuple[EndpointRule, ...]
        Immutable collection of rules added at construction time.
    """

    def __init__(self, rules: Sequence[EndpointRule] | None = None) -> None:
        self.rules = tuple(rules or ())

    def match(self, method: EndpointMethod, path: EndpointPath) -> EndpointRule | None:
        """Return the first rule that matches *method* + *path*, or ``None``.

        Parameters
        ----------
        method: str
            The HTTP method of the incoming request (case‑insensitive).
        path: str
            The request URL path (including leading ``/``).

        Returns
        -------
        EndpointRule | None
            The matching rule, or ``None`` when no rule matches.
        """
        method_upper = method.upper()
        for rule in self.rules:
            if rule.method != method_upper:
                continue
            if self._path_matches(rule.path, path):
                return rule
        return None

    # ------------------------------------------------------------------
    # Segment‑wise path matching – ``{param}`` matches any segment
    # ------------------------------------------------------------------
    @staticmethod
    def _path_matches(pattern: str, request_path: str) -> bool:
        """True iff *pattern* (may contain ``{param}``) equals *request_path*.

        Both strings are normalised by stripping leading/trailing ``/`` and
        splitting on ``/``.  The number of segments must be equal; a
        ``{param}`` placeholder matches any single segment.
        """
        # Remove leading/trailing slashes and split
        pat_parts = [p for p in pattern.strip("/").split("/") if p]
        req_parts = [p for p in request_path.strip("/").split("/") if p]

        if len(pat_parts) != len(req_parts):
            return False

        for pat, req in zip(pat_parts, req_parts):
            # A ``{...}`` placeholder matches any single segment
            if not (pat.startswith("{") and pat.endswith("}")) and pat != req:
                return False
        return True
