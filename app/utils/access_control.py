"""Access control utilities for 4-layer security model."""
from flask_login import current_user
from app.models.user import AccessLevel


class AccessControl:
    """Access control helper class."""

    @staticmethod
    def can_view_customer(customer):
        """Check if current user can view a customer."""
        if not current_user.is_authenticated:
            return False

        return current_user.can_access_customer(customer)

    @staticmethod
    def can_edit_customer(customer):
        """Check if current user can edit a customer."""
        if not current_user.is_authenticated:
            return False

        # Individual level can only edit own customers
        if current_user.access_level == AccessLevel.INDIVIDUAL:
            return customer.owner_id == current_user.id

        # Higher levels can edit customers in their organizational units
        return current_user.can_access_organizational_unit(customer.organizational_unit_id)

    @staticmethod
    def can_delete_customer(customer):
        """Check if current user can delete a customer."""
        if not current_user.is_authenticated:
            return False

        # Only branch level and above can delete
        if current_user.access_level == AccessLevel.INDIVIDUAL:
            return False

        return current_user.can_access_organizational_unit(customer.organizational_unit_id)

    @staticmethod
    def can_reassign_customer(customer):
        """Check if current user can reassign a customer to another user."""
        if not current_user.is_authenticated:
            return False

        # Only branch level and above can reassign
        if current_user.access_level == AccessLevel.INDIVIDUAL:
            return False

        return current_user.can_access_organizational_unit(customer.organizational_unit_id)

    @staticmethod
    def can_view_opportunity(opportunity):
        """Check if current user can view an opportunity."""
        if not current_user.is_authenticated:
            return False

        # Check customer access (opportunity follows customer access)
        return current_user.can_access_customer(opportunity.customer)

    @staticmethod
    def can_view_sensitive_data():
        """Check if user can view sensitive data (full account numbers, high net worth details)."""
        if not current_user.is_authenticated:
            return False

        # Only BRANCH level and above can view full sensitive data
        return current_user.access_level.value <= AccessLevel.BRANCH.value

    @staticmethod
    def mask_account_number(account_number):
        """Mask account number for non-privileged users."""
        if not account_number:
            return ''

        if AccessControl.can_view_sensitive_data():
            return account_number

        # Show only last 4 digits
        if len(account_number) > 4:
            return '*' * (len(account_number) - 4) + account_number[-4:]
        return '****'

    @staticmethod
    def can_approve_opportunity(opportunity):
        """Check if user can approve opportunities."""
        if not current_user.is_authenticated:
            return False

        # Only managers and above can approve
        if current_user.access_level.value > AccessLevel.BRANCH.value:
            return False

        return current_user.can_access_organizational_unit(opportunity.organizational_unit_id)

    @staticmethod
    def can_set_targets():
        """Check if user can set targets."""
        if not current_user.is_authenticated:
            return False

        # Only BRANCH level and above can set targets
        return current_user.access_level.value <= AccessLevel.BRANCH.value

    @staticmethod
    def can_view_analytics():
        """Check if user can view analytics dashboard."""
        if not current_user.is_authenticated:
            return False

        # Regional and Executive can view full analytics
        # Branch can view their own analytics
        return current_user.access_level.value <= AccessLevel.BRANCH.value

    @staticmethod
    def get_accessible_user_ids():
        """Get list of user IDs accessible to current user."""
        if not current_user.is_authenticated:
            return []

        if current_user.access_level == AccessLevel.EXECUTIVE:
            from app.models.user import User
            return [u.id for u in User.query.all()]

        # Get users in accessible organizational units
        accessible_units = current_user.get_accessible_organizational_units()
        from app.models.user import User
        user_ids = []
        for unit in accessible_units:
            user_ids.extend([u.id for u in unit.users.all()])

        return user_ids
