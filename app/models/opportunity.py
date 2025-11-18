"""Opportunity and deal management models."""
from datetime import datetime
from enum import Enum

from app import db


class OpportunityStage(Enum):
    """Deal pipeline stages."""
    IDENTIFICATION = 'identification'
    QUALIFICATION = 'qualification'
    PROPOSAL = 'proposal'
    NEGOTIATION = 'negotiation'
    CLOSING = 'closing'
    WON = 'won'
    LOST = 'lost'
    POST_SALE = 'post_sale'


class ProductLine(Enum):
    """Banking product lines."""
    RETAIL_LOAN = 'retail_loan'
    MORTGAGE = 'mortgage'
    CREDIT_CARD = 'credit_card'
    SAVINGS_ACCOUNT = 'savings_account'
    CURRENT_ACCOUNT = 'current_account'
    INVESTMENT = 'investment'
    INSURANCE = 'insurance'
    SME_LOAN = 'sme_loan'
    CORPORATE_FINANCE = 'corporate_finance'
    TRADE_FINANCE = 'trade_finance'


class LostReason(Enum):
    """Reasons for lost opportunities."""
    PRICE = 'price'
    COMPETITOR = 'competitor'
    NO_RESPONSE = 'no_response'
    TIMING = 'timing'
    NO_NEED = 'no_need'
    CREDIT_REJECTED = 'credit_rejected'
    OTHER = 'other'


class Opportunity(db.Model):
    """Opportunity/Deal model."""
    __tablename__ = 'opportunities'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)

    # Product & Pipeline
    product_line = db.Column(db.Enum(ProductLine), nullable=False, index=True)
    stage = db.Column(db.Enum(OpportunityStage), nullable=False, default=OpportunityStage.IDENTIFICATION, index=True)

    # Financial
    amount = db.Column(db.Numeric(15, 2), nullable=False)  # Deal value
    probability = db.Column(db.Integer, default=10)  # 0-100 percentage
    expected_revenue = db.Column(db.Numeric(15, 2))  # amount * probability
    actual_revenue = db.Column(db.Numeric(15, 2))  # Final revenue if won

    # Dates
    expected_close_date = db.Column(db.Date, index=True)
    actual_close_date = db.Column(db.Date)

    # Ownership
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    organizational_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=False)

    # Win/Loss Analysis
    is_active = db.Column(db.Boolean, default=True, index=True)
    won_date = db.Column(db.DateTime)
    lost_date = db.Column(db.DateTime)
    lost_reason = db.Column(db.Enum(LostReason))
    lost_notes = db.Column(db.Text)
    competitor_name = db.Column(db.String(100))

    # Approval Workflow
    requires_approval = db.Column(db.Boolean, default=False)
    approval_status = db.Column(db.String(20))  # 'pending', 'approved', 'rejected'
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_date = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text)

    # Cross-sell/Up-sell
    is_cross_sell = db.Column(db.Boolean, default=False)
    is_upsell = db.Column(db.Boolean, default=False)
    parent_opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='opportunities')
    owner = db.relationship('User', foreign_keys=[owner_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    organizational_unit = db.relationship('OrganizationalUnit')
    activities = db.relationship('Activity', back_populates='opportunity', lazy='dynamic')
    parent_opportunity = db.relationship('Opportunity', remote_side=[id], backref='child_opportunities')

    def __repr__(self):
        return f'<Opportunity {self.name} - {self.stage.value}>'

    def update_expected_revenue(self):
        """Calculate expected revenue based on amount and probability."""
        if self.amount and self.probability:
            self.expected_revenue = self.amount * (self.probability / 100)

    def advance_stage(self, new_stage):
        """Advance opportunity to next stage with probability updates."""
        self.stage = new_stage

        # Update probability based on stage
        stage_probabilities = {
            OpportunityStage.IDENTIFICATION: 10,
            OpportunityStage.QUALIFICATION: 20,
            OpportunityStage.PROPOSAL: 40,
            OpportunityStage.NEGOTIATION: 60,
            OpportunityStage.CLOSING: 80,
            OpportunityStage.WON: 100,
            OpportunityStage.LOST: 0,
        }

        if new_stage in stage_probabilities:
            self.probability = stage_probabilities[new_stage]
            self.update_expected_revenue()

        if new_stage == OpportunityStage.WON:
            self.is_active = False
            self.won_date = datetime.utcnow()
            self.actual_close_date = datetime.utcnow().date()
            self.actual_revenue = self.amount

        elif new_stage == OpportunityStage.LOST:
            self.is_active = False
            self.lost_date = datetime.utcnow()
            self.actual_close_date = datetime.utcnow().date()

    def mark_won(self, actual_revenue=None):
        """Mark opportunity as won."""
        self.advance_stage(OpportunityStage.WON)
        if actual_revenue:
            self.actual_revenue = actual_revenue

    def mark_lost(self, reason, notes=None, competitor=None):
        """Mark opportunity as lost with reason."""
        self.advance_stage(OpportunityStage.LOST)
        self.lost_reason = reason
        self.lost_notes = notes
        self.competitor_name = competitor
