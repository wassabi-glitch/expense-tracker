"""Smoke tests proving the domain package split compatibility surface works.

These tests verify that:
1. All domain packages are importable
2. All compat shims re-export the same symbols
3. The full app can be imported
4. Key cross-package imports resolve correctly
"""

import pytest


class TestDomainPackageImports:
    """Verify all domain package __init__ modules are importable."""

    def test_ledger_domain_imports(self):
        from app.domains.ledger import (
            PostEntityLeg,
            PostWalletLeg,
            post_financial_event,
        )
        assert post_financial_event is not None
        assert PostWalletLeg is not None
        assert PostEntityLeg is not None

    def test_posting_domain_imports(self):
        from app.domains.posting import (
            ExpensePostingResult,
            post_expense_event,
            resolve_expense_wallet_allocations,
            validate_active_expense_category,
            validate_real_expense_category,
        )
        assert post_expense_event is not None
        assert ExpensePostingResult is not None
        assert resolve_expense_wallet_allocations is not None
        assert validate_active_expense_category is not None
        assert validate_real_expense_category is not None

    def test_budget_permission_domain_imports(self):
        from app.domains.budget_permission import (
            BudgetPermissionRequest,
            BudgetPermissionResult,
            check_budget_permission,
        )
        assert check_budget_permission is not None
        assert BudgetPermissionRequest is not None
        assert BudgetPermissionResult is not None

    def test_budget_reporting_domain_imports(self):
        from app.domains.budget_reporting import (
            compute_budget_chain,
            materialize_budget_for_month,
            recompute_budget_chain,
        )
        assert compute_budget_chain is not None
        assert materialize_budget_for_month is not None
        assert recompute_budget_chain is not None

    def test_debt_domain_imports(self):
        from app.domains.debt import (
            create_debt_ledger_entry,
            create_debt_payment,
            evaluate_debt_action,
            evaluate_debt_actions,
            is_pristine_debt,
            reconcile_debt,
        )
        assert create_debt_ledger_entry is not None
        assert create_debt_payment is not None
        assert evaluate_debt_action is not None
        assert evaluate_debt_actions is not None
        assert is_pristine_debt is not None
        assert reconcile_debt is not None

    def test_payment_plans_domain_imports(self):
        from app.domains.payment_plans import (
            _add_months,
            _add_years,
            _create_payment_plan_expense_event,
            _scheduled_due_date,
        )
        assert _create_payment_plan_expense_event is not None
        assert _scheduled_due_date is not None
        assert _add_months is not None
        assert _add_years is not None


class TestCompatShimImports:
    """Verify all compat shims re-export the same symbols as the originals."""

    def test_financial_event_ledger_compat_shim(self):
        from app.services.financial_event_ledger_service import (
            PostEntityLeg,
            PostWalletLeg,
            post_financial_event,
        )
        from app.domains.ledger import (
            PostEntityLeg as DomainPostEntityLeg,
            PostWalletLeg as DomainPostWalletLeg,
            post_financial_event as domain_post,
        )
        assert post_financial_event is domain_post
        assert PostWalletLeg is DomainPostWalletLeg
        assert PostEntityLeg is DomainPostEntityLeg

    def test_expense_posting_compat_shim(self):
        from app.services.expense_posting_service import (
            ExpensePostingResult,
            post_expense_event,
        )
        from app.domains.posting import (
            ExpensePostingResult as DomainResult,
            post_expense_event as domain_post,
        )
        assert post_expense_event is domain_post
        assert ExpensePostingResult is DomainResult

    def test_category_policy_compat_shim(self):
        from app.services.category_policy import validate_active_expense_category
        from app.domains.posting import validate_active_expense_category as domain_validate
        assert validate_active_expense_category is domain_validate

    def test_budget_permission_compat_shim(self):
        from app.services.budget_permission_service import check_budget_permission
        from app.domains.budget_permission import check_budget_permission as domain_check
        assert check_budget_permission is domain_check

    def test_budget_service_compat_shim(self):
        from app.services.budget_service import compute_budget_chain
        from app.domains.budget_reporting import compute_budget_chain as domain_compute
        assert compute_budget_chain is domain_compute

    def test_debt_service_compat_shim(self):
        from app.services.debt_service import reconcile_debt
        from app.domains.debt import reconcile_debt as domain_reconcile
        assert reconcile_debt is domain_reconcile

    def test_debt_payment_service_compat_shim(self):
        from app.services.debt_payment_service import create_debt_payment
        from app.domains.debt import create_debt_payment as domain_create
        assert create_debt_payment is domain_create

    def test_debt_policy_compat_shim(self):
        from app.services.debt_policy import evaluate_debt_action
        from app.domains.debt import evaluate_debt_action as domain_eval
        assert evaluate_debt_action is domain_eval


class TestDomainSeparation:
    """Prove Debt and Payment Plan domains remain separate."""

    def test_debt_and_payment_plan_have_separate_init_modules(self):
        """Debt and Payment Plan must have distinct package surfaces."""
        import app.domains.debt
        import app.domains.payment_plans
        assert app.domains.debt.__file__ != app.domains.payment_plans.__file__

    def test_debt_does_not_export_payment_plan_symbols(self):
        """Debt domain must not export Payment Plan symbols."""
        import app.domains.debt
        assert not hasattr(app.domains.debt, "_create_payment_plan_expense_event")
        assert not hasattr(app.domains.debt, "_scheduled_due_date")

    def test_payment_plans_does_not_export_debt_lifecycle(self):
        """Payment Plan domain must not export Debt lifecycle symbols."""
        import app.domains.payment_plans
        assert not hasattr(app.domains.payment_plans, "reconcile_debt")
        assert not hasattr(app.domains.payment_plans, "evaluate_debt_action")
        assert not hasattr(app.domains.payment_plans, "is_pristine_debt")

    def test_budget_permission_and_reporting_have_separate_init_modules(self):
        """Budget Permission and Budget Reporting must have distinct package surfaces."""
        import app.domains.budget_permission
        import app.domains.budget_reporting
        assert app.domains.budget_permission.__file__ != app.domains.budget_reporting.__file__


class TestFullAppImport:
    """Verify the full application still imports successfully."""

    def test_full_app_import(self):
        """The FastAPI app must import without errors after the package split."""
        from app.main import app
        assert app is not None
        assert hasattr(app, "router")
