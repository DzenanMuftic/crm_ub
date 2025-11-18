"""Target management blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.models.target import Target, TargetType, TargetPeriod, TargetAchievement
from app.models.user import User, AccessLevel
from app.utils.decorators import require_access_level, audit_action
from app.utils.access_control import AccessControl

targets_bp = Blueprint('targets', __name__, url_prefix='/targets')


@targets_bp.route('/')
@login_required
def index():
    """List targets."""
    # Individual users see their own targets
    # Managers see their team's targets
    # Executives see all targets

    if current_user.access_level == AccessLevel.INDIVIDUAL:
        targets = Target.query.filter_by(user_id=current_user.id, is_active=True).all()
    else:
        accessible_user_ids = AccessControl.get_accessible_user_ids()
        targets = Target.query.filter(
            Target.user_id.in_(accessible_user_ids),
            Target.is_active == True
        ).all()

    # Calculate current status for each target
    for target in targets:
        target.calculate_achievement()

    db.session.commit()

    return render_template('targets/index.html', targets=targets)


@targets_bp.route('/<int:id>')
@login_required
@audit_action('view', 'target')
def view(id):
    """View target details with achievements."""
    target = Target.query.get_or_404(id)

    # Check access
    if current_user.access_level == AccessLevel.INDIVIDUAL:
        if target.user_id != current_user.id:
            flash('Nemate dozvolu za pristup ovom cilju.', 'danger')
            return redirect(url_for('targets.index'))

    achievements = target.achievements.order_by(TargetAchievement.achievement_date.desc()).all()

    return render_template('targets/view.html',
                         target=target,
                         achievements=achievements,
                         is_on_track=target.is_on_track())


@targets_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
@audit_action('create', 'target')
def create():
    """Create new target (managers and above only)."""
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        target = Target(
            name=request.form.get('name'),
            description=request.form.get('description'),
            target_type=TargetType[request.form.get('target_type')],
            period_type=TargetPeriod[request.form.get('period_type')],
            start_date=datetime.strptime(start_date_str, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date_str, '%Y-%m-%d').date(),
            target_value=request.form.get('target_value', type=float),
            product_line=request.form.get('product_line') or None,
            customer_segment=request.form.get('customer_segment') or None
        )

        # Assignment: either to user or organizational unit
        user_id = request.form.get('user_id', type=int)
        org_unit_id = request.form.get('organizational_unit_id', type=int)

        if user_id:
            target.user_id = user_id
        elif org_unit_id:
            target.organizational_unit_id = org_unit_id
        else:
            flash('Morate dodijeliti cilj korisniku ili organizacionoj jedinici.', 'danger')
            return redirect(url_for('targets.create'))

        db.session.add(target)
        db.session.commit()

        flash(f'Cilj {target.name} uspješno kreiran.', 'success')
        return redirect(url_for('targets.view', id=target.id))

    # Get accessible users for assignment
    accessible_user_ids = AccessControl.get_accessible_user_ids()
    users = User.query.filter(User.id.in_(accessible_user_ids)).order_by(User.last_name).all()

    # Get accessible organizational units
    org_units = current_user.get_accessible_organizational_units()

    return render_template('targets/create.html',
                         users=users,
                         org_units=org_units,
                         target_types=TargetType,
                         period_types=TargetPeriod)


@targets_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_access_level('BRANCH', 'REGIONAL', 'EXECUTIVE')
@audit_action('update', 'target')
def edit(id):
    """Edit target."""
    target = Target.query.get_or_404(id)

    if request.method == 'POST':
        target.name = request.form.get('name')
        target.description = request.form.get('description')
        target.target_value = request.form.get('target_value', type=float)

        db.session.commit()

        flash('Cilj uspješno ažuriran.', 'success')
        return redirect(url_for('targets.view', id=id))

    return render_template('targets/edit.html', target=target)


@targets_bp.route('/dashboard')
@login_required
def dashboard():
    """Target dashboard with progress visualization."""
    today = datetime.utcnow().date()

    # Get active targets
    if current_user.access_level == AccessLevel.INDIVIDUAL:
        targets = Target.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).filter(
            Target.start_date <= today,
            Target.end_date >= today
        ).all()
    else:
        accessible_user_ids = AccessControl.get_accessible_user_ids()
        targets = Target.query.filter(
            Target.user_id.in_(accessible_user_ids),
            Target.is_active == True
        ).filter(
            Target.start_date <= today,
            Target.end_date >= today
        ).all()

    # Update calculations
    for target in targets:
        target.calculate_achievement()

    db.session.commit()

    return render_template('targets/dashboard.html', targets=targets)


@targets_bp.route('/api/<int:id>/progress')
@login_required
def api_progress(id):
    """API endpoint for target progress data."""
    target = Target.query.get_or_404(id)

    # Check access
    if current_user.access_level == AccessLevel.INDIVIDUAL:
        if target.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

    target.calculate_achievement()

    return jsonify({
        'target_value': float(target.target_value),
        'achieved_value': float(target.achieved_value),
        'achievement_percentage': target.achievement_percentage,
        'is_on_track': target.is_on_track(),
        'start_date': target.start_date.isoformat(),
        'end_date': target.end_date.isoformat()
    })
