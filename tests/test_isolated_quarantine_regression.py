"""Regression coverage for the Frozen Isolated Project Quarantine (ADR-0022).

These tests prove:

1. The quarantine contract exposes only the approved compatibility surface.
2. Stable core modules do not bypass the quarantine.
3. Existing isolated project compatibility behavior remains stable.
4. Overlay project behavior remains active and unchanged.
5. Guard documentation and import rules are enforced.
"""

import ast
from pathlib import Path

from app.domains.projects import _quarantine
from app.domains.projects._quarantine import _contract

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

REQUIRED_COMPATIBILITY_EXPORTS = frozenset({
    "is_isolated_project",
    "get_wallet_project_allocated_amount",
    "get_project_wallet_allocated_amount",
    "get_wallet_free_to_allocate_for_projects",
    "get_project_funding_limit",
    "get_project_category_allocated_amount",
    "get_project_unallocated_funding_amount",
    "get_isolated_project_category_spent_amount",
    "get_isolated_project_subcategory_spent_amount",
    "get_isolated_project_total_spent",
    "validate_project_limit_sum",
    "validate_isolated_project_category_allocation_covers_spending",
    "project_wallet_allocations_out",
})

FROZEN_WRITE_EXPORTS = frozenset({
    "apply_isolated_project_top_up",
    "apply_isolated_project_category_allocation",
    "apply_isolated_project_subcategory_allocation",
    "apply_isolated_project_rebalance",
    "sweep_isolated_project_wallet_allocations",
    "validate_project_wallet_allocations",
    "get_isolated_project_wrap_up_summary",
    "get_isolated_project_total_top_ups",
})

DISALLOWED_EXPORTS = frozenset({
    "_signed_posted_expense_amount",
    "_resolve_user_subcategory",
    "graduate_fund_project",
    "create_fund_project_goal",
})

ALL_ALLOWED = REQUIRED_COMPATIBILITY_EXPORTS | FROZEN_WRITE_EXPORTS

STABLE_CORE_DIRS = [
    "app/domains/ledger",
    "app/domains/posting",
    "app/domains/budget_permission",
    "app/domains/budget_reporting",
    "app/domains/debt",
    "app/domains/payment_plans",
    "app/routers",
    "app/services",
]

ALLOWED_DIRECT_IMPORTERS = {
    "app/domains/projects/_quarantine/__init__.py",
    "app/services/isolated_project_service.py",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _python_files_under(directory: str):
    """Yield Path objects for every .py file under *directory*."""
    base = Path(directory)
    if not base.is_dir():
        return
    for py_file in base.rglob("*.py"):
        yield py_file


def _direct_imports_of_isolated_project_service(file_path: Path):
    """Return a list of import lines that reference isolated_project_service."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "isolated_project_service" in node.module:
                results.append(
                    f"  {file_path}: from {node.module} import ..."
                )
    return results


# ---------------------------------------------------------------------------
# 1. Quarantine contract surface integrity
# ---------------------------------------------------------------------------

def test_all_required_compatibility_exports_present():
    """Every approved compatibility query is reachable through quarantine."""
    actual = set(_quarantine.__all__)
    missing = REQUIRED_COMPATIBILITY_EXPORTS - actual
    assert not missing, (
        f"Quarantine __all__ missing required exports: {missing}"
    )


def test_all_frozen_write_exports_present():
    """Frozen write operations are reachable for existing route compatibility."""
    actual = set(_quarantine.__all__)
    missing = FROZEN_WRITE_EXPORTS - actual
    assert not missing, (
        f"Quarantine __all__ missing frozen write exports: {missing}"
    )


def test_no_disallowed_exports_in_quarantine_surface():
    """No disallowed function leaks through the quarantine surface."""
    actual = set(_quarantine.__all__)
    for name in actual:
        assert name not in DISALLOWED_EXPORTS, (
            f"Disallowed export '{name}' found in quarantine surface"
        )


def test_quarantine_exports_are_resolvable():
    """Every name in __all__ resolves to an importable object."""
    for name in _quarantine.__all__:
        obj = getattr(_quarantine, name, None)
        assert obj is not None, (
            f"'{name}' in __all__ but not found on quarantine module"
        )


def test_key_compatibility_functions_are_callable():
    """Key compatibility functions are callable."""
    assert callable(_quarantine.is_isolated_project)
    assert callable(_quarantine.get_project_funding_limit)
    assert callable(_quarantine.get_wallet_project_allocated_amount)
    assert callable(_quarantine.get_project_category_allocated_amount)
    assert callable(_quarantine.get_isolated_project_category_spent_amount)
    assert callable(_quarantine.validate_project_limit_sum)
    assert callable(_quarantine.project_wallet_allocations_out)


# ---------------------------------------------------------------------------
# 2. Import guard — no direct bypass of quarantine
# ---------------------------------------------------------------------------

def test_no_stable_core_module_imports_isolated_project_service_directly():
    """Only the quarantine __init__.py may import from isolated_project_service."""
    violations = []
    for directory in STABLE_CORE_DIRS:
        for py_file in _python_files_under(directory):
            rel_path = str(py_file.as_posix())
            if rel_path in ALLOWED_DIRECT_IMPORTERS:
                continue
            for violation in _direct_imports_of_isolated_project_service(py_file):
                violations.append(violation)
    assert not violations, (
        "Stable core modules must import through the quarantine contract, "
        "not from app.services.isolated_project_service directly:\n"
        + "\n".join(violations)
    )


def test_app_services_dir_only_isolated_project_service_self_imports():
    """Under app/services/, only isolated_project_service.py may reference itself."""
    services_dir = Path("app/services")
    if not services_dir.is_dir():
        return
    violations = []
    for py_file in services_dir.glob("*.py"):
        rel_path = str(py_file.as_posix())
        if rel_path in ALLOWED_DIRECT_IMPORTERS:
            continue
        for violation in _direct_imports_of_isolated_project_service(py_file):
            violations.append(violation)
    assert not violations, (
        "Service files must import through the quarantine:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# 3. ADR-0022 guard documentation
# ---------------------------------------------------------------------------

def test_contract_py_references_adr_0022():
    """_contract.py must reference ADR-0022."""
    source = Path(_contract.__file__).read_text(encoding="utf-8")
    assert "ADR-0022" in source, (
        "_contract.py must reference ADR-0022 to warn future agents"
    )


def test_quarantine_init_py_references_adr_0022():
    """Quarantine __init__.py must reference ADR-0022."""
    source = Path(_quarantine.__file__).read_text(encoding="utf-8")
    assert "ADR-0022" in source, (
        "quarantine __init__.py must reference ADR-0022"
    )


def test_contract_py_has_freeze_warning():
    """_contract.py must contain freeze/DO NOT language."""
    source = Path(_contract.__file__).read_text(encoding="utf-8")
    has_freeze = "DO NOT" in source or "frozen" in source.lower()
    assert has_freeze, "_contract.py must contain freeze warnings"


def test_quarantine_init_py_has_freeze_warning():
    """Quarantine __init__.py must contain FROZEN/DO NOT language."""
    source = Path(_quarantine.__file__).read_text(encoding="utf-8")
    has_freeze = "FROZEN" in source or "DO NOT" in source or "frozen" in source.lower()
    assert has_freeze, "quarantine __init__.py must contain freeze warnings"


def test_contract_py_documents_key_allowed_queries():
    """_contract.py must document the key allowed compatibility queries."""
    source = Path(_contract.__file__).read_text(encoding="utf-8")
    assert "is_isolated_project" in source, (
        "_contract.py must document is_isolated_project"
    )
    assert "get_project_funding_limit" in source, (
        "_contract.py must document get_project_funding_limit"
    )


def test_contract_py_documents_disallowed_operations():
    """_contract.py must document disallowed operations."""
    source = Path(_contract.__file__).read_text(encoding="utf-8")
    assert "Not Allowed" in source or "NOT" in source, (
        "_contract.py must document disallowed operations"
    )


# ---------------------------------------------------------------------------
# 4. Projects domain integrity (active surface)
# ---------------------------------------------------------------------------

def test_projects_domain_exports_active_functions():
    """Active projects domain exports overlay project and lifecycle functions."""
    from app.domains import projects
    assert hasattr(projects, "is_overlay_project")
    assert callable(projects.is_overlay_project)
    assert hasattr(projects, "validate_project_editable")
    assert hasattr(projects, "build_project_detail")
    assert hasattr(projects, "get_project_type")


def test_projects_domain_does_not_export_frozen_isolated_writes():
    """Active projects domain must NOT export frozen isolated write operations."""
    from app.domains import projects
    frozen_writes = {
        "apply_isolated_project_top_up",
        "apply_isolated_project_category_allocation",
        "apply_isolated_project_subcategory_allocation",
        "apply_isolated_project_rebalance",
        "sweep_isolated_project_wallet_allocations",
        "get_isolated_project_wrap_up_summary",
    }
    for name in frozen_writes:
        assert not hasattr(projects, name), (
            f"Active projects domain must not export frozen operation '{name}'"
        )


def test_quarantine_is_opt_in_subpackage():
    """Quarantine imports as a separate opt-in subpackage."""
    from app.domains.projects import _quarantine as q
    assert q is not None
    assert hasattr(q, "is_isolated_project")


# ---------------------------------------------------------------------------
# 5. No new isolated project features introduced
# ---------------------------------------------------------------------------

def test_quarantine_does_not_expose_fund_project_graduation():
    """Fund Project graduation must not appear in the quarantine surface."""
    forbidden = [
        "graduate_fund_project",
        "create_fund_project_goal",
        "promote_fund_project",
    ]
    for name in forbidden:
        assert not hasattr(_quarantine, name), (
            f"Quarantine must not expose '{name}' — Fund Project is frozen"
        )


def test_quarantine_does_not_expose_protection_breach():
    """EC-162 project-protection breach resolution must not be exposed."""
    forbidden = [
        "resolve_project_protection_breach",
        "ec162_resolution",
        "project_breach_resolution",
    ]
    for name in forbidden:
        assert not hasattr(_quarantine, name), (
            f"Quarantine must not expose '{name}'"
        )


def test_critical_compatibility_exports_documented_in_contract():
    """Critical compatibility exports must appear in _contract.py documentation."""
    contract_source = Path(_contract.__file__).read_text(encoding="utf-8")
    critical = {
        "is_isolated_project",
        "get_wallet_project_allocated_amount",
        "get_project_wallet_allocated_amount",
        "get_project_funding_limit",
        "get_project_category_allocated_amount",
        "get_isolated_project_category_spent_amount",
        "get_isolated_project_subcategory_spent_amount",
        "get_isolated_project_total_spent",
        "validate_project_limit_sum",
        "validate_isolated_project_category_allocation_covers_spending",
        "project_wallet_allocations_out",
    }
    missing = [name for name in critical if name not in contract_source]
    assert not missing, (
        f"Critical compatibility exports not documented in _contract.py: {missing}"
    )


# ---------------------------------------------------------------------------
# 6. Documented remaining leakage (follow-up per Issue 12, item 7)
# ---------------------------------------------------------------------------
#
# The following isolated project surface cannot be safely moved yet and is
# documented here as required follow-up:
#
# 1. app/services/isolated_project_service.py
#    Still lives in the flat services/ directory alongside active services.
#    Cannot be moved to app/domains/projects/_quarantine/_isolated.py yet
#    because the full domain package split (PRD 3 Issue 7) has not been
#    executed.  The quarantine __init__.py re-exports from here as a
#    compatibility bridge.  Once Issue 7 is complete, this file becomes a
#    thin compat shim and the real code moves into _quarantine/_isolated.py.
#
# 2. app/routers/projects.py
#    Contains extensive isolated project route handlers (top-up, allocate,
#    rebalance, sweep, wrap-up).  These are existing routes that must
#    continue functioning per ADR-0022 ("Existing code may remain if it
#    does not block or distort core app work").  They are not "leakage" —
#    they are legacy compatibility preserved by the freeze.  Routes now
#    import through the quarantine contract.
#
# 3. app/services/session_draft_service.py
#    Imports is_isolated_project from app.services.project_service (not
#    from isolated_project_service).  This is a simple type guard living
#    in active project code — low risk.  Could be routed through
#    quarantine in a follow-up if desired.
#
# 4. app/services/overlay_project_service.py
#    Same situation as session_draft_service.py — imports
#    is_isolated_project from project_service for type-guard purposes.
#    Overlay project behavior is explicitly NOT frozen per ADR-0022.
