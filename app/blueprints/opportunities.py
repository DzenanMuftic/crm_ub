"""Opportunity and deal management blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.opportunity import Opportunity, OpportunityStage, ProductLine, LostReason
from app.models.customer import Customer
from app.utils.decorators import audit_action, require_access_level
from app.utils.access_control import AccessControl
from app.utils.query_filters import apply_opportunity_filter

opportunities_bp = Blueprint('opportunities', __name__, url_prefix='/opportunities')


@opportunities_bp.route('/')
@login_required
def index():
    """List opportunities with filtering."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    stage = request.args.get('stage', '')
    product_line = request.args.get('product_line', '')
    active_only = request.args.get('active_only', 'true') == 'true'

    # Base query with access control
    query = apply_opportunity_filter(Opportunity.query)

    # Apply filters
    if active_only:
        query = query.filter_by(is_active=True)

    if stage:
        try:
            query = query.filter_by(stage=OpportunityStage[stage.upper()])
        except KeyError:
            pass

    if product_line:
        try:
            query = query.filter_by(product_line=ProductLine[product_line.upper()])
        except KeyError:
            pass

    # Order by expected close date
    query = query.order_by(Opportunity.expected_close_date.asc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    opportunities = pagination.items

    # Calculate pipeline value
    pipeline_value = db.session.query(func.sum(Opportunity.expected_revenue)).filter(
        Opportunity.is_active == True,
        Opportunity.id.in_([o.id for o in apply_opportunity_filter(Opportunity.query).filter_by(is_active=True).all()])
    ).scalar() or 0

    return render_template('opportunities/index.html',
                         opportunities=opportunities,
                         pagination=pagination,
                         stages=OpportunityStage,
                         product_lines=ProductLine,
                         current_stage=stage,
                         current_product_line=product_line,
                         active_only=active_only,
                         pipeline_value=pipeline_value)


@opportunities_bp.route('/<int:id>')
@login_required
@audit_action('view', 'opportunity')
def view(id):
    """View opportunity details."""
    opportunity = Opportunity.query.get_or_404(id)

    if not AccessControl.can_view_opportunity(opportunity):
        flash('Nemate dozvolu za pristup ovoj prilici.', 'danger')
        return redirect(url_for('opportunities.index'))

    # Get related data
    activities = opportunity.activities.order_by('activity_date desc').all()

    return render_template('opportunities/view.html',
                         opportunity=opportunity,
                         activities=activities,
                         can_approve=AccessControl.can_approve_opportunity(opportunity))


@opportunities_bp.route('/create', methods=['GET', 'POST'])
@login_required
@audit_action('create', 'opportunity')
def create():
    """Create new opportunity."""
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        customer = Customer.query.get_or_404(customer_id)

        if not AccessControl.can_view_customer(customer):
            flash('Nemate dozvolu za pristup ovom klijentu.', 'danger')
            return redirect(url_for('customers.index'))

        amount = request.form.get('amount', type=float)
        probability = request.form.get('probability', 10, type=int)

        opportunity = Opportunity(
            name=request.form.get('name'),
            description=request.form.get('description'),
            customer_id=customer_id,
            product_line=ProductLine[request.form.get('product_line')],
            amount=amount,
            probability=probability,
            owner_id=current_user.id,
            organizational_unit_id=current_user.organizational_unit_id
        )

        # Parse expected close date
        expected_close_date_str = request.form.get('expected_close_date')
        if expected_close_date_str:
            opportunity.expected_close_date = datetime.strptime(expected_close_date_str, '%Y-%m-%d').date()

        opportunity.update_expected_revenue()

        db.session.add(opportunity)
        db.session.commit()

        flash(f'Prilika {opportunity.name} uspješno kreirana.', 'success')
        return redirect(url_for('opportunities.view', id=opportunity.id))

    # Get accessible customers for dropdown
    from app.utils.query_filters import apply_customer_filter
    customers = apply_customer_filter(Customer.query).order_by(Customer.last_name).all()

    return render_template('opportunities/create.html',
                         customers=customers,
                         product_lines=ProductLine)


@opportunities_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@audit_action('update', 'opportunity')
def edit(id):
    """Edit opportunity."""
    opportunity = Opportunity.query.get_or_404(id)

    if not AccessControl.can_view_opportunity(opportunity):
        flash('Nemate dozvolu za uređivanje ove prilike.', 'danger')
        return redirect(url_for('opportunities.view', id=id))

    if request.method == 'POST':
        opportunity.name = request.form.get('name')
        opportunity.description = request.form.get('description')
        opportunity.product_line = ProductLine[request.form.get('product_line')]
        opportunity.amount = request.form.get('amount', type=float)
        opportunity.probability = request.form.get('probability', type=int)

        expected_close_date_str = request.form.get('expected_close_date')
        if expected_close_date_str:
            opportunity.expected_close_date = datetime.strptime(expected_close_date_str, '%Y-%m-%d').date()

        opportunity.update_expected_revenue()

        db.session.commit()

        flash('Prilika uspješno ažurirana.', 'success')
        return redirect(url_for('opportunities.view', id=id))

    return render_template('opportunities/edit.html',
                         opportunity=opportunity,
                         product_lines=ProductLine)


@opportunities_bp.route('/<int:id>/advance-stage', methods=['POST'])
@login_required
@audit_action('advance_stage', 'opportunity')
def advance_stage(id):
    """Advance opportunity to next stage."""
    opportunity = Opportunity.query.get_or_404(id)

    if not AccessControl.can_view_opportunity(opportunity):
        flash('Nemate dozvolu za uređivanje ove prilike.', 'danger')
        return redirect(url_for('opportunities.view', id=id))

    new_stage = request.form.get('new_stage')
    try:
        opportunity.advance_stage(OpportunityStage[new_stage])
        db.session.commit()

        flash(f'Prilika premještena u fazu: {new_stage}', 'success')
    except Exception as e:
        flash(f'Greška: {str(e)}', 'danger')

    return redirect(url_for('opportunities.view', id=id))


@opportunities_bp.route('/<int:id>/mark-won', methods=['POST'])
@login_required
@audit_action('mark_won', 'opportunity')
def mark_won(id):
    """Mark opportunity as won."""
    opportunity = Opportunity.query.get_or_404(id)

    if not AccessControl.can_view_opportunity(opportunity):
        flash('Nemate dozvolu za uređivanje ove prilike.', 'danger')
        return redirect(url_for('opportunities.view', id=id))

    actual_revenue = request.form.get('actual_revenue', type=float)
    opportunity.mark_won(actual_revenue=actual_revenue)

    # Update target achievement
    from app.models.target import Target, TargetType, TargetAchievement
    active_targets = Target.query.filter_by(
        user_id=current_user.id,
        target_type=TargetType.REVENUE,
        is_active=True
    ).filter(
        Target.start_date <= datetime.utcnow().date(),
        Target.end_date >= datetime.utcnow().date()
    ).all()

    for target in active_targets:
        achievement = TargetAchievement(
            target_id=target.id,
            opportunity_id=opportunity.id,
            achieved_value=actual_revenue or opportunity.amount,
            achievement_date=datetime.utcnow().date()
        )
        db.session.add(achievement)
        target.update_achievement(actual_revenue or opportunity.amount)

    db.session.commit()

    flash('Prilika označena kao dobivena!', 'success')
    return redirect(url_for('opportunities.view', id=id))


@opportunities_bp.route('/<int:id>/mark-lost', methods=['POST'])
@login_required
@audit_action('mark_lost', 'opportunity')
def mark_lost(id):
    """Mark opportunity as lost."""
    opportunity = Opportunity.query.get_or_404(id)

    if not AccessControl.can_view_opportunity(opportunity):
        flash('Nemate dozvolu za uređivanje ove prilike.', 'danger')
        return redirect(url_for('opportunities.view', id=id))

    reason = LostReason[request.form.get('lost_reason')]
    notes = request.form.get('lost_notes')
    competitor = request.form.get('competitor_name')

    opportunity.mark_lost(reason=reason, notes=notes, competitor=competitor)
    db.session.commit()

    flash('Prilika označena kao izgubljena.', 'info')
    return redirect(url_for('opportunities.view', id=id))


@opportunities_bp.route('/pipeline')
@login_required
def pipeline():
    """Pipeline view with kanban board."""
    query = apply_opportunity_filter(Opportunity.query).filter_by(is_active=True)

    # Group opportunities by stage
    pipeline_data = {}
    for stage in OpportunityStage:
        if stage in [OpportunityStage.WON, OpportunityStage.LOST, OpportunityStage.POST_SALE]:
            continue
        opportunities = query.filter_by(stage=stage).order_by(Opportunity.expected_close_date).all()
        stage_value = sum([float(o.expected_revenue or 0) for o in opportunities])
        pipeline_data[stage] = {
            'opportunities': opportunities,
            'count': len(opportunities),
            'value': stage_value
        }

    return render_template('opportunities/pipeline.html',
                         pipeline_data=pipeline_data,
                         stages=OpportunityStage)
