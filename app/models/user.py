"""User and access control models."""
from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class AccessLevel(Enum):
    """4-Layer access control hierarchy."""
    EXECUTIVE = 1      # C-Suite/Executive - Full system access
    REGIONAL = 2       # Regional/Divisional Management
    BRANCH = 3         # Branch/Team Managers
    INDIVIDUAL = 4     # Relationship Managers/Sales Staff


class Role(Enum):
    """User roles for functional permissions."""
    ADMIN = 'admin'
    SALES = 'sales'
    SERVICE = 'service'
    SUPPORT = 'support'
    ANALYST = 'analyst'
    MANAGER = 'manager'


class OrganizationalUnit(db.Model):
    """Hierarchical organizational structure."""
    __tablename__ = 'organizational_units'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'division', 'region', 'branch', 'team'
    parent_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    parent = db.relationship('OrganizationalUnit', remote_side=[id], backref='children')
    users = db.relationship('User', back_populates='organizational_unit', lazy='dynamic')

    def __repr__(self):
        return f'<OrgUnit {self.code}: {self.name}>'

    def get_hierarchy_path(self):
        """Get full path from root to this unit."""
        path = [self]
        current = self.parent
        while current:
            path.insert(0, current)
            current = current.parent
        return path

    def get_all_children(self):
        """Get all child units recursively."""
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.get_all_children())
        return children


class User(UserMixin, db.Model):
    """User model with 4-layer access control."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))

    # Access control
    access_level = db.Column(db.Enum(AccessLevel), nullable=False, default=AccessLevel.INDIVIDUAL)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.SALES)
    organizational_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=False)

    # Product line restrictions (JSON array of allowed product lines)
    product_restrictions = db.Column(db.JSON, default=list)

    # Preferences
    language = db.Column(db.String(5), default='bs')  # bs, en, tr

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organizational_unit = db.relationship('OrganizationalUnit', back_populates='users')
    owned_customers = db.relationship('Customer', back_populates='owner', foreign_keys='Customer.owner_id')
    tasks = db.relationship('Task', back_populates='assigned_to', foreign_keys='Task.assigned_to_id')
    activities = db.relationship('Activity', back_populates='user', foreign_keys='Activity.user_id')
    targets = db.relationship('Target', back_populates='user', foreign_keys='Target.user_id')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password."""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """Get full name."""
        return f"{self.first_name} {self.last_name}"

    def can_access_organizational_unit(self, org_unit_id):
        """Check if user can access data from a specific organizational unit."""
        if self.access_level == AccessLevel.EXECUTIVE:
            return True

        if self.organizational_unit_id == org_unit_id:
            return True

        # Check if org_unit is a child of user's unit
        if self.access_level in [AccessLevel.REGIONAL, AccessLevel.BRANCH]:
            from app.models.user import OrganizationalUnit
            target_unit = OrganizationalUnit.query.get(org_unit_id)
            if target_unit:
                children = self.organizational_unit.get_all_children()
                return target_unit in children

        return False

    def get_accessible_organizational_units(self):
        """Get all organizational units this user can access."""
        if self.access_level == AccessLevel.EXECUTIVE:
            return OrganizationalUnit.query.all()

        accessible = [self.organizational_unit]

        if self.access_level in [AccessLevel.REGIONAL, AccessLevel.BRANCH]:
            accessible.extend(self.organizational_unit.get_all_children())

        return accessible

    def can_access_customer(self, customer):
        """Check if user can access a specific customer."""
        # Individual level can only access own customers
        if self.access_level == AccessLevel.INDIVIDUAL:
            return customer.owner_id == self.id

        # Higher levels can access customers in their organizational units
        return self.can_access_organizational_unit(customer.organizational_unit_id)

    def has_role(self, *roles):
        """Check if user has any of the specified roles."""
        return self.role in roles
