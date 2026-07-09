"""Domain packages — stable seams for the ExpenseTracker backend.

Each sub-package owns one domain and exposes a narrow public interface
through its ``__init__.py``.  Internal modules are prefixed with ``_``
and should not be imported directly by code outside the package.

See ``codebase-improvement/domain-package-split-map.md`` for the full
package map, dependency order, and compatibility strategy.
"""
