"""Query filters for automatic access control enforcement."""
from flask_login import current_user
from sqlalchemy import or_

from app.models.user import AccessLevel


def apply_access_filter(query, model):
    """
    Apply access control filter to SQLAlchemy query.
    This enforces data isolation at the database query level.
    """
    if not current_user.is_authenticated:
        # Return empty query for unauthenticated users
        return query.filter(model.id == None)

    # Executive level has full access
    if current_user.access_level == AccessLevel.EXECUTIVE:
        return query

    # Get accessible organizational unit IDs
    accessible_units = current_user.get_accessible_organizational_units()
    accessible_unit_ids = [unit.id for unit in accessible_units]

    # Individual level can only see their own records
    if current_user.access_level == AccessLevel.INDIVIDUAL:
        # Check if model has owner_id
        if hasattr(model, 'owner_id'):
            return query.filter(model.owner_id == current_user.id)
        # Fallback to organizational unit filter
        elif hasattr(model, 'organizational_unit_id'):
            return query.filter(model.organizational_unit_id.in_(accessible_unit_ids))
        else:
            return query

    # Regional and Branch levels: filter by organizational units
    if hasattr(model, 'organizational_unit_id'):
        return query.filter(model.organizational_unit_id.in_(accessible_unit_ids))

    return query


def apply_customer_filter(query):
    """Apply access filter specifically for Customer model."""
    from app.models.customer import Customer
    return apply_access_filter(query, Customer)


def apply_opportunity_filter(query):
    """Apply access filter specifically for Opportunity model."""
    from app.models.opportunity import Opportunity
    return apply_access_filter(query, Opportunity)


def apply_task_filter(query):
    """Apply access filter for tasks (can see assigned or created tasks)."""
    from app.models.activity import Task

    if not current_user.is_authenticated:
        return query.filter(Task.id == None)

    if current_user.access_level == AccessLevel.EXECUTIVE:
        return query

    # Users can see tasks assigned to them or assigned by them
    if current_user.access_level == AccessLevel.INDIVIDUAL:
        return query.filter(
            or_(
                Task.assigned_to_id == current_user.id,
                Task.assigned_by_id == current_user.id
            )
        )

    # Higher levels can see all tasks in their organizational units
    accessible_units = current_user.get_accessible_organizational_units()
    accessible_user_ids = []
    for unit in accessible_units:
        accessible_user_ids.extend([u.id for u in unit.users.all()])

    return query.filter(
        or_(
            Task.assigned_to_id.in_(accessible_user_ids),
            Task.assigned_by_id.in_(accessible_user_ids)
        )
    )
