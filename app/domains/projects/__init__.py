"""Projects domain — project lifecycle, overlay projects, and budget views.

**Frozen Isolated Project compatibility is quarantined** in ``_quarantine/``.
Import from ``app.domains.projects._quarantine`` only when you need isolated
project compatibility queries.  See ADR-0022 for the freeze decision.

Active (non-frozen) surface
---------------------------
- ``is_overlay_project`` — type guard for overlay projects
- ``get_project_type`` — resolve project type enum
- ``get_owned_project_subcategory_or_404`` — project subcategory lookup
- ``validate_project_editable`` — guard against editing completed/archived projects
- ``validate_project_update_rules`` — cross-type update validation
- ``validate_project_completion_date`` — completion date guard
- ``validate_overlay_project_deletion_target`` — overlay-only deletion guard
- ``delete_pristine_overlay_project`` — safe delete for unlinked projects
- ``detach_project_expenses_and_delete`` — detach + delete overlay projects
- ``cascade_void_project_expenses_and_delete`` — void-linked + delete overlay projects
- ``get_project_deletion_preview`` — linked-event preview for deletion
- ``build_project_detail`` — full project detail with financial breakdown
- ``count_project_linked_events`` — count of linked financial events
- ``earliest_project_event_date`` — earliest linked event date
- ``latest_project_event_date`` — latest linked event date
"""

from app.services.project_service import (  # noqa: F401
    build_project_detail,
    cascade_void_project_expenses_and_delete,
    count_project_linked_events,
    delete_pristine_overlay_project,
    detach_project_expenses_and_delete,
    earliest_project_event_date,
    get_owned_project_subcategory_or_404,
    get_project_deletion_preview,
    get_project_type,
    is_overlay_project,
    latest_project_event_date,
    validate_overlay_project_deletion_target,
    validate_project_completion_date,
    validate_project_editable,
    validate_project_update_rules,
)

__all__ = [
    "build_project_detail",
    "cascade_void_project_expenses_and_delete",
    "count_project_linked_events",
    "delete_pristine_overlay_project",
    "detach_project_expenses_and_delete",
    "earliest_project_event_date",
    "get_owned_project_subcategory_or_404",
    "get_project_deletion_preview",
    "get_project_type",
    "is_overlay_project",
    "latest_project_event_date",
    "validate_overlay_project_deletion_target",
    "validate_project_completion_date",
    "validate_project_editable",
    "validate_project_update_rules",
]
