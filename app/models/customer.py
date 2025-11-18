"""Customer lifecycle models."""
from datetime import datetime
from enum import Enum

from app import db


class CustomerStage(Enum):
    """Customer lifecycle stages."""
    SUSPECT = 'suspect'          # Unqualified contacts
    PROSPECT = 'prospect'        # Qualified potential customers
    LEAD = 'lead'               # Active sales pursuit
    CUSTOMER = 'customer'        # Active customer
    INACTIVE = 'inactive'        # Inactive/churned customer


class CustomerSegment(Enum):
    """Customer segments."""
    RETAIL = 'retail'
    SME = 'sme'
    CORPORATE = 'corporate'
    PRIVATE_BANKING = 'private_banking'


class Customer(db.Model):
    """Customer/Lead model with 360° view."""
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(200))  # For corporate customers
    email = db.Column(db.String(120), index=True)
    phone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))

    # Address
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(2), default='BA')

    # Customer Classification
    stage = db.Column(db.Enum(CustomerStage), nullable=False, default=CustomerStage.SUSPECT, index=True)
    segment = db.Column(db.Enum(CustomerSegment), nullable=False, default=CustomerSegment.RETAIL)
    qualification_score = db.Column(db.Integer, default=0)  # 0-100 scoring

    # Financial Information (masked for non-privileged users)
    estimated_assets = db.Column(db.Numeric(15, 2))
    estimated_income = db.Column(db.Numeric(15, 2))
    credit_score = db.Column(db.Integer)
    is_high_net_worth = db.Column(db.Boolean, default=False)  # Extra security layer

    # CBS Integration
    cbs_customer_id = db.Column(db.String(50), unique=True, index=True)  # Core Banking System ID

    # Ownership & Access Control
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    organizational_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=False, index=True)

    # Source & Campaign
    source = db.Column(db.String(50))  # 'referral', 'campaign', 'walk-in', etc.
    campaign_id = db.Column(db.String(50))
    referrer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))

    # Lifecycle Tracking
    suspect_date = db.Column(db.DateTime)
    prospect_date = db.Column(db.DateTime)
    lead_date = db.Column(db.DateTime)
    customer_date = db.Column(db.DateTime)
    last_contact_date = db.Column(db.DateTime)
    next_follow_up = db.Column(db.DateTime)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    do_not_contact = db.Column(db.Boolean, default=False)

    # Compliance
    kyc_status = db.Column(db.String(20), default='pending')  # 'pending', 'verified', 'rejected'
    kyc_verified_date = db.Column(db.DateTime)
    aml_status = db.Column(db.String(20), default='clear')  # 'clear', 'flagged', 'under_review'
    consent_marketing = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship('User', back_populates='owned_customers', foreign_keys=[owner_id])
    organizational_unit = db.relationship('OrganizationalUnit')
    notes = db.relationship('CustomerNote', back_populates='customer', lazy='dynamic', cascade='all, delete-orphan')
    opportunities = db.relationship('Opportunity', back_populates='customer', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', back_populates='customer', lazy='dynamic', cascade='all, delete-orphan')
    referrals = db.relationship('Customer', backref=db.backref('referrer', remote_side=[id]))

    def __repr__(self):
        return f'<Customer {self.full_name} ({self.stage.value})>'

    @property
    def full_name(self):
        """Get full name."""
        if self.company_name:
            return self.company_name
        return f"{self.first_name} {self.last_name}"

    def advance_stage(self, new_stage):
        """Advance customer to next lifecycle stage."""
        self.stage = new_stage

        if new_stage == CustomerStage.PROSPECT:
            self.prospect_date = datetime.utcnow()
        elif new_stage == CustomerStage.LEAD:
            self.lead_date = datetime.utcnow()
        elif new_stage == CustomerStage.CUSTOMER:
            self.customer_date = datetime.utcnow()

    def calculate_qualification_score(self):
        """Calculate qualification score based on available data."""
        score = 0

        # Contact information (20 points)
        if self.email:
            score += 10
        if self.mobile or self.phone:
            score += 10

        # Financial information (40 points)
        if self.estimated_assets:
            score += 20
        if self.credit_score and self.credit_score > 600:
            score += 20

        # Engagement (40 points)
        if self.last_contact_date:
            days_since_contact = (datetime.utcnow() - self.last_contact_date).days
            if days_since_contact < 7:
                score += 20
            elif days_since_contact < 30:
                score += 10

        if self.opportunities.filter_by(is_active=True).count() > 0:
            score += 20

        self.qualification_score = min(score, 100)
        return self.qualification_score


class CustomerNote(db.Model):
    """Notes and interactions with customers."""
    __tablename__ = 'customer_notes'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    note_type = db.Column(db.String(20), default='general')  # 'general', 'call', 'meeting', 'email'
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)

    is_important = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    customer = db.relationship('Customer', back_populates='notes')
    user = db.relationship('User')

    def __repr__(self):
        return f'<CustomerNote {self.id} for Customer {self.customer_id}>'
