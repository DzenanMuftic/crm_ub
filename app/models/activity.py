"""Activity and task management models."""
from datetime import datetime
from enum import Enum

from app import db


class ActivityType(Enum):
    """Types of activities."""
    CALL = 'call'
    EMAIL = 'email'
    MEETING = 'meeting'
    NOTE = 'note'
    TASK = 'task'
    SMS = 'sms'
    WHATSAPP = 'whatsapp'


class TaskStatus(Enum):
    """Task statuses."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    OVERDUE = 'overdue'


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'


class Activity(db.Model):
    """Activity tracking for customer interactions."""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)

    # Classification
    activity_type = db.Column(db.Enum(ActivityType), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Associations
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Timing
    activity_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    duration_minutes = db.Column(db.Integer)  # Call/meeting duration

    # Outcome
    outcome = db.Column(db.String(50))  # 'successful', 'no_answer', 'follow_up_needed', etc.
    next_action = db.Column(db.String(200))
    next_action_date = db.Column(db.DateTime)

    # Location (for field activities)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='activities')
    opportunity = db.relationship('Opportunity', back_populates='activities')
    user = db.relationship('User', back_populates='activities', foreign_keys=[user_id])

    def __repr__(self):
        return f'<Activity {self.activity_type.value}: {self.subject}>'


class Task(db.Model):
    """Task management with SLA tracking."""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Classification
    priority = db.Column(db.Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM, index=True)
    status = db.Column(db.Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    task_type = db.Column(db.String(50))  # 'follow_up', 'documentation', 'approval', etc.

    # Associations
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True, index=True)

    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Timing & SLA
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    sla_hours = db.Column(db.Integer)  # SLA in hours
    sla_deadline = db.Column(db.DateTime)
    is_overdue = db.Column(db.Boolean, default=False, index=True)
    completed_date = db.Column(db.DateTime)

    # Escalation
    escalation_level = db.Column(db.Integer, default=0)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    escalation_date = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer')
    opportunity = db.relationship('Opportunity')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], back_populates='tasks')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    escalated_to = db.relationship('User', foreign_keys=[escalated_to_id])

    def __repr__(self):
        return f'<Task {self.title} - {self.status.value}>'

    def check_overdue(self):
        """Check if task is overdue and update status."""
        if self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            if self.due_date < datetime.utcnow():
                self.is_overdue = True
                self.status = TaskStatus.OVERDUE
                return True
        return False

    def complete(self):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_date = datetime.utcnow()
        self.is_overdue = False

    def escalate(self, escalated_to_user_id):
        """Escalate task to higher level."""
        self.escalation_level += 1
        self.escalated_to_id = escalated_to_user_id
        self.escalation_date = datetime.utcnow()


class Meeting(db.Model):
    """Meeting management with calendar integration."""
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    meeting_url = db.Column(db.String(500))  # For video meetings

    # Associations
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True, index=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Timing
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)

    # Meeting Details
    agenda = db.Column(db.Text)
    pre_meeting_notes = db.Column(db.Text)  # Auto-generated briefing
    meeting_notes = db.Column(db.Text)
    outcome = db.Column(db.String(50))
    follow_up_actions = db.Column(db.Text)

    # Status
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    is_reminder_sent = db.Column(db.Boolean, default=False)

    # Calendar Integration
    calendar_event_id = db.Column(db.String(200))
    calendar_provider = db.Column(db.String(20))  # 'google', 'outlook'

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer')
    opportunity = db.relationship('Opportunity')
    organizer = db.relationship('User')

    def __repr__(self):
        return f'<Meeting {self.title} at {self.start_time}>'

    def generate_pre_meeting_briefing(self):
        """Generate pre-meeting briefing with customer history."""
        if not self.customer:
            return

        briefing = f"Meeting Briefing: {self.customer.full_name}\n\n"
        briefing += f"Customer Stage: {self.customer.stage.value}\n"
        briefing += f"Owner: {self.customer.owner.full_name}\n"

        # Recent activities
        recent_activities = self.customer.activities.order_by(Activity.activity_date.desc()).limit(5).all()
        if recent_activities:
            briefing += "\nRecent Activities:\n"
            for activity in recent_activities:
                briefing += f"- {activity.activity_date.strftime('%Y-%m-%d')}: {activity.subject}\n"

        # Active opportunities
        opportunities = self.customer.opportunities.filter_by(is_active=True).all()
        if opportunities:
            briefing += "\nActive Opportunities:\n"
            for opp in opportunities:
                briefing += f"- {opp.name}: {opp.stage.value} ({opp.amount} BAM)\n"

        self.pre_meeting_notes = briefing
