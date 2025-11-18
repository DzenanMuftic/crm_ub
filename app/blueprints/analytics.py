"""Analytics and reporting blueprint."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, extract

from app import db
from app.models.customer import Customer, CustomerStage, CustomerSegment
from app.models.opportunity import Opportunity, OpportunityStage, ProductLine
from app.models.user import AccessLevel
from app.utils.decorators import require_access_level
from app.utils.query_filters import apply_customer_filter, apply_opportunity_filter
from app.utils.access_control import AccessControl

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def index():
    """Analytics dashboard."""
    return render_template('analytics/index.html')


@analytics_bp.route('/customers')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def customers():
    """Customer analytics."""
    # Apply access control
    query = apply_customer_filter(Customer.query)

    # By stage
    by_stage = {}
    for stage in CustomerStage:
        count = query.filter_by(stage=stage).count()
        by_stage[stage.value] = count

    # By segment
    by_segment = {}
    for segment in CustomerSegment:
        count = query.filter_by(segment=segment).count()
        by_segment[segment.value] = count

    # Conversion funnel
    total_suspects = query.filter_by(stage=CustomerStage.SUSPECT).count()
    total_prospects = query.filter_by(stage=CustomerStage.PROSPECT).count()
    total_leads = query.filter_by(stage=CustomerStage.LEAD).count()
    total_customers = query.filter_by(stage=CustomerStage.CUSTOMER).count()

    # Monthly trend (last 12 months)
    monthly_data = []
    for i in range(11, -1, -1):
        month_date = datetime.utcnow().date() - timedelta(days=i*30)
        month_start = month_date.replace(day=1)

        customers = query.filter(
            Customer.customer_date >= month_start,
            Customer.customer_date < month_start + timedelta(days=30),
            Customer.stage == CustomerStage.CUSTOMER
        ).count()

        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': customers
        })

    return render_template('analytics/customers.html',
                         by_stage=by_stage,
                         by_segment=by_segment,
                         funnel={
                             'suspects': total_suspects,
                             'prospects': total_prospects,
                             'leads': total_leads,
                             'customers': total_customers
                         },
                         monthly_data=monthly_data)


@analytics_bp.route('/pipeline')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def pipeline():
    """Pipeline analytics."""
    query = apply_opportunity_filter(Opportunity.query).filter_by(is_active=True)

    # By stage
    by_stage = {}
    stage_values = {}
    for stage in OpportunityStage:
        opps = query.filter_by(stage=stage).all()
        by_stage[stage.value] = len(opps)
        stage_values[stage.value] = sum([float(o.expected_revenue or 0) for o in opps])

    # By product line
    by_product = {}
    for product in ProductLine:
        count = query.filter_by(product_line=product).count()
        by_product[product.value] = count

    # Win/loss analysis (last quarter)
    quarter_ago = datetime.utcnow() - timedelta(days=90)
    won_count = apply_opportunity_filter(Opportunity.query).filter(
        Opportunity.won_date >= quarter_ago,
        Opportunity.stage == OpportunityStage.WON
    ).count()

    lost_count = apply_opportunity_filter(Opportunity.query).filter(
        Opportunity.lost_date >= quarter_ago,
        Opportunity.stage == OpportunityStage.LOST
    ).count()

    win_rate = (won_count / (won_count + lost_count) * 100) if (won_count + lost_count) > 0 else 0

    # Revenue forecast
    total_pipeline_value = sum(stage_values.values())

    return render_template('analytics/pipeline.html',
                         by_stage=by_stage,
                         stage_values=stage_values,
                         by_product=by_product,
                         won_count=won_count,
                         lost_count=lost_count,
                         win_rate=win_rate,
                         total_pipeline_value=total_pipeline_value)


@analytics_bp.route('/team-performance')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def team_performance():
    """Team performance analytics."""
    # Get accessible users
    accessible_user_ids = AccessControl.get_accessible_user_ids()
    from app.models.user import User

    users = User.query.filter(User.id.in_(accessible_user_ids)).all()

    # Calculate metrics for each user
    user_metrics = []
    for user in users:
        # Customer count
        customers = Customer.query.filter_by(
            owner_id=user.id,
            stage=CustomerStage.CUSTOMER
        ).count()

        # Active opportunities
        opportunities = Opportunity.query.filter_by(
            owner_id=user.id,
            is_active=True
        ).count()

        # Won this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        won_revenue = db.session.query(func.sum(Opportunity.actual_revenue)).filter(
            Opportunity.owner_id == user.id,
            Opportunity.won_date >= month_ago,
            Opportunity.stage == OpportunityStage.WON
        ).scalar() or 0

        user_metrics.append({
            'user': user,
            'customers': customers,
            'opportunities': opportunities,
            'revenue': float(won_revenue)
        })

    # Sort by revenue
    user_metrics.sort(key=lambda x: x['revenue'], reverse=True)

    return render_template('analytics/team_performance.html',
                         user_metrics=user_metrics)


@analytics_bp.route('/api/conversion-rates')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def api_conversion_rates():
    """API endpoint for conversion rate data."""
    query = apply_customer_filter(Customer.query)

    total = query.count()
    if total == 0:
        return jsonify({'error': 'No data'}), 404

    suspects = query.filter_by(stage=CustomerStage.SUSPECT).count()
    prospects = query.filter_by(stage=CustomerStage.PROSPECT).count()
    leads = query.filter_by(stage=CustomerStage.LEAD).count()
    customers = query.filter_by(stage=CustomerStage.CUSTOMER).count()

    return jsonify({
        'suspect_to_prospect': (prospects / suspects * 100) if suspects > 0 else 0,
        'prospect_to_lead': (leads / prospects * 100) if prospects > 0 else 0,
        'lead_to_customer': (customers / leads * 100) if leads > 0 else 0
    })


@analytics_bp.route('/api/revenue-forecast')
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
def api_revenue_forecast():
    """API endpoint for revenue forecast."""
    query = apply_opportunity_filter(Opportunity.query).filter_by(is_active=True)

    # Group by month of expected close
    forecast = {}
    for i in range(6):  # Next 6 months
        month_date = datetime.utcnow().date() + timedelta(days=i*30)
        month_key = month_date.strftime('%Y-%m')

        month_revenue = db.session.query(func.sum(Opportunity.expected_revenue)).filter(
            Opportunity.is_active == True,
            extract('year', Opportunity.expected_close_date) == month_date.year,
            extract('month', Opportunity.expected_close_date) == month_date.month,
            Opportunity.id.in_([o.id for o in query.all()])
        ).scalar() or 0

        forecast[month_key] = float(month_revenue)

    return jsonify(forecast)
