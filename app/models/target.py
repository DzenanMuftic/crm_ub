"""Target management and performance tracking models."""
from datetime import datetime
from enum import Enum

from app import db


class TargetType(Enum):
    """Types of targets."""
    REVENUE = 'revenue'
    NEW_CUSTOMERS = 'new_customers'
    PRODUCT_SALES = 'product_sales'
    PORTFOLIO_GROWTH = 'portfolio_growth'
    CROSS_SELL = 'cross_sell'


class TargetPeriod(Enum):
    """Target period types."""
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    ANNUALLY = 'annually'


class Target(db.Model):
    """Target allocation and tracking."""
    __tablename__ = 'targets'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_type = db.Column(db.Enum(TargetType), nullable=False, index=True)

    # Period
    period_type = db.Column(db.Enum(TargetPeriod), nullable=False)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)

    # Assignment (hierarchical)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    organizational_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=True, index=True)

    # Product/Segment specific
    product_line = db.Column(db.String(50))  # Specific product line
    customer_segment = db.Column(db.String(50))  # Specific customer segment

    # Target Values
    target_value = db.Column(db.Numeric(15, 2), nullable=False)
    achieved_value = db.Column(db.Numeric(15, 2), default=0)
    achievement_percentage = db.Column(db.Float, default=0)

    # Status
    is_active = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='targets', foreign_keys=[user_id])
    organizational_unit = db.relationship('OrganizationalUnit')
    achievements = db.relationship('TargetAchievement', back_populates='target', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Target {self.name} - {self.achievement_percentage}%>'

    def calculate_achievement(self):
        """Calculate achievement percentage."""
        if self.target_value > 0:
            self.achievement_percentage = (float(self.achieved_value) / float(self.target_value)) * 100
        else:
            self.achievement_percentage = 0
        return self.achievement_percentage

    def update_achievement(self, additional_value):
        """Update achieved value and recalculate percentage."""
        self.achieved_value += additional_value
        self.calculate_achievement()

    def is_on_track(self):
        """Check if target is on track based on time elapsed."""
        now = datetime.utcnow().date()
        if now < self.start_date or now > self.end_date:
            return None

        total_days = (self.end_date - self.start_date).days
        elapsed_days = (now - self.start_date).days

        if total_days == 0:
            return True

        expected_percentage = (elapsed_days / total_days) * 100
        return self.achievement_percentage >= expected_percentage


class TargetAchievement(db.Model):
    """Individual achievement records for targets."""
    __tablename__ = 'target_achievements'

    id = db.Column(db.Integer, primary_key=True)

    # Association
    target_id = db.Column(db.Integer, db.ForeignKey('targets.id'), nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)

    # Achievement Details
    achieved_value = db.Column(db.Numeric(15, 2), nullable=False)
    achievement_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    target = db.relationship('Target', back_populates='achievements')
    opportunity = db.relationship('Opportunity')
    customer = db.relationship('Customer')

    def __repr__(self):
        return f'<TargetAchievement {self.achieved_value} for Target {self.target_id}>'
