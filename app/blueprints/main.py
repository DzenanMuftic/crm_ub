"""Main blueprint for dashboard and home."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.customer import Customer, CustomerStage
from app.models.opportunity import Opportunity, OpportunityStage
from app.models.activity import Task, TaskStatus
from app.models.target import Target
from app.utils.query_filters import apply_customer_filter, apply_opportunity_filter, apply_task_filter

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with KPIs and recent activity."""
    # Date ranges
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Apply access control filters
    customers_query = apply_customer_filter(Customer.query)
    opportunities_query = apply_opportunity_filter(Opportunity.query)
    tasks_query = apply_task_filter(Task.query)

    # Customer statistics
    total_customers = customers_query.filter_by(stage=CustomerStage.CUSTOMER).count()
    total_leads = customers_query.filter(Customer.stage.in_([CustomerStage.LEAD, CustomerStage.PROSPECT])).count()
    new_customers_this_month = customers_query.filter(
        Customer.customer_date >= month_ago,
        Customer.stage == CustomerStage.CUSTOMER
    ).count()

    # Opportunity statistics
    active_opportunities = opportunities_query.filter_by(is_active=True).count()
    opportunities_value = db.session.query(func.sum(Opportunity.expected_revenue)).filter(
        Opportunity.is_active == True,
        Opportunity.id.in_([o.id for o in opportunities_query.filter_by(is_active=True).all()])
    ).scalar() or 0

    won_this_month = opportunities_query.filter(
        Opportunity.won_date >= month_ago,
        Opportunity.stage == OpportunityStage.WON
    ).count()

    won_value_this_month = db.session.query(func.sum(Opportunity.actual_revenue)).filter(
        Opportunity.won_date >= month_ago,
        Opportunity.stage == OpportunityStage.WON,
        Opportunity.id.in_([o.id for o in opportunities_query.all()])
    ).scalar() or 0

    # Task statistics
    my_pending_tasks = tasks_query.filter(
        Task.assigned_to_id == current_user.id,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
    ).count()

    my_overdue_tasks = tasks_query.filter(
        Task.assigned_to_id == current_user.id,
        Task.status == TaskStatus.OVERDUE
    ).count()

    # Target progress (current user)
    active_targets = Target.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).filter(
        Target.start_date <= today,
        Target.end_date >= today
    ).all()

    # Recent activities
    recent_customers = customers_query.order_by(Customer.created_at.desc()).limit(5).all()
    recent_opportunities = opportunities_query.filter_by(is_active=True).order_by(Opportunity.created_at.desc()).limit(5).all()
    upcoming_tasks = tasks_query.filter(
        Task.assigned_to_id == current_user.id,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
    ).order_by(Task.due_date.asc()).limit(5).all()

    return render_template('dashboard/index.html',
                         total_customers=total_customers,
                         total_leads=total_leads,
                         new_customers_this_month=new_customers_this_month,
                         active_opportunities=active_opportunities,
                         opportunities_value=opportunities_value,
                         won_this_month=won_this_month,
                         won_value_this_month=won_value_this_month,
                         my_pending_tasks=my_pending_tasks,
                         my_overdue_tasks=my_overdue_tasks,
                         active_targets=active_targets,
                         recent_customers=recent_customers,
                         recent_opportunities=recent_opportunities,
                         upcoming_tasks=upcoming_tasks)


@main_bp.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard statistics (for charts)."""
    # Monthly trend for last 6 months
    from dateutil.relativedelta import relativedelta

    months = []
    customers_trend = []
    revenue_trend = []

    for i in range(5, -1, -1):
        month_date = datetime.utcnow().date() - relativedelta(months=i)
        month_start = month_date.replace(day=1)
        if i == 0:
            month_end = datetime.utcnow().date()
        else:
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        months.append(month_start.strftime('%b %Y'))

        # Customer count
        customers_query = apply_customer_filter(Customer.query)
        customer_count = customers_query.filter(
            Customer.customer_date >= month_start,
            Customer.customer_date <= month_end,
            Customer.stage == CustomerStage.CUSTOMER
        ).count()
        customers_trend.append(customer_count)

        # Revenue
        opportunities_query = apply_opportunity_filter(Opportunity.query)
        revenue = db.session.query(func.sum(Opportunity.actual_revenue)).filter(
            Opportunity.won_date >= month_start,
            Opportunity.won_date <= month_end,
            Opportunity.stage == OpportunityStage.WON,
            Opportunity.id.in_([o.id for o in opportunities_query.all()])
        ).scalar() or 0
        revenue_trend.append(float(revenue))

    return jsonify({
        'months': months,
        'customers': customers_trend,
        'revenue': revenue_trend
    })


from flask import url_for, redirect

# Import after blueprint definition to avoid circular imports
