from fastapi import HTTPException, status

from app import models


DEPRECATED_FINANCING_CONTEXT_CATEGORIES = {
    models.ExpenseCategory.PAYMENT_PLANS_DEBT,
}


def is_deprecated_financing_context_category(category: models.ExpenseCategory) -> bool:
    return category in DEPRECATED_FINANCING_CONTEXT_CATEGORIES


def validate_active_expense_category(
    category: models.ExpenseCategory,
    *,
    error_detail: str = "categories.validation.real_expense_category_required",
) -> None:
    if is_deprecated_financing_context_category(category):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )
