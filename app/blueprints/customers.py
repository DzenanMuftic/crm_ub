"""Customer lifecycle management blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.models.customer import Customer, CustomerStage, CustomerSegment, CustomerNote
from app.models.activity import Activity, ActivityType
from app.utils.decorators import audit_action
from app.utils.access_control import AccessControl
from app.utils.query_filters import apply_customer_filter

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
def index():
    """List customers with filtering and pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    stage = request.args.get('stage', '')
    segment = request.args.get('segment', '')
    search = request.args.get('search', '')

    # Base query with access control
    query = apply_customer_filter(Customer.query)

    # Apply filters
    if stage:
        try:
            query = query.filter_by(stage=CustomerStage[stage.upper()])
        except KeyError:
            pass

    if segment:
        try:
            query = query.filter_by(segment=CustomerSegment[segment.upper()])
        except KeyError:
            pass

    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            (Customer.first_name.ilike(search_pattern)) |
            (Customer.last_name.ilike(search_pattern)) |
            (Customer.company_name.ilike(search_pattern)) |
            (Customer.email.ilike(search_pattern))
        )

    # Order by most recently updated
    query = query.order_by(Customer.updated_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    customers = pagination.items

    return render_template('customers/index.html',
                         customers=customers,
                         pagination=pagination,
                         stages=CustomerStage,
                         segments=CustomerSegment,
                         current_stage=stage,
                         current_segment=segment,
                         search=search)


@customers_bp.route('/<int:id>')
@login_required
@audit_action('view', 'customer')
def view(id):
    """View customer details (360° view)."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_view_customer(customer):
        flash('Nemate dozvolu za pristup ovom klijentu.', 'danger')
        return redirect(url_for('customers.index'))

    # Get related data
    notes = customer.notes.order_by(CustomerNote.created_at.desc()).all()
    opportunities = customer.opportunities.order_by('created_at desc').all()
    activities = customer.activities.order_by('activity_date desc').limit(20).all()

    return render_template('customers/view.html',
                         customer=customer,
                         notes=notes,
                         opportunities=opportunities,
                         activities=activities,
                         can_edit=AccessControl.can_edit_customer(customer))


@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@audit_action('create', 'customer')
def create():
    """Create new customer/lead."""
    if request.method == 'POST':
        customer = Customer(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            company_name=request.form.get('company_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            mobile=request.form.get('mobile'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            postal_code=request.form.get('postal_code'),
            stage=CustomerStage[request.form.get('stage', 'SUSPECT')],
            segment=CustomerSegment[request.form.get('segment', 'RETAIL')],
            source=request.form.get('source'),
            owner_id=current_user.id,
            organizational_unit_id=current_user.organizational_unit_id,
            suspect_date=datetime.utcnow()
        )

        db.session.add(customer)
        db.session.commit()

        flash(f'Klijent {customer.full_name} uspješno kreiran.', 'success')
        return redirect(url_for('customers.view', id=customer.id))

    return render_template('customers/create.html',
                         stages=CustomerStage,
                         segments=CustomerSegment)


@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@audit_action('update', 'customer')
def edit(id):
    """Edit customer details."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_edit_customer(customer):
        flash('Nemate dozvolu za uređivanje ovog klijenta.', 'danger')
        return redirect(url_for('customers.view', id=id))

    if request.method == 'POST':
        customer.first_name = request.form.get('first_name')
        customer.last_name = request.form.get('last_name')
        customer.company_name = request.form.get('company_name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.mobile = request.form.get('mobile')
        customer.address = request.form.get('address')
        customer.city = request.form.get('city')
        customer.postal_code = request.form.get('postal_code')
        customer.segment = CustomerSegment[request.form.get('segment')]

        db.session.commit()

        flash('Podaci o klijentu uspješno ažurirani.', 'success')
        return redirect(url_for('customers.view', id=id))

    return render_template('customers/edit.html',
                         customer=customer,
                         segments=CustomerSegment)


@customers_bp.route('/<int:id>/advance-stage', methods=['POST'])
@login_required
@audit_action('advance_stage', 'customer')
def advance_stage(id):
    """Advance customer to next lifecycle stage."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_edit_customer(customer):
        flash('Nemate dozvolu za uređivanje ovog klijenta.', 'danger')
        return redirect(url_for('customers.view', id=id))

    new_stage = request.form.get('new_stage')
    try:
        customer.advance_stage(CustomerStage[new_stage])
        db.session.commit()

        flash(f'Klijent premješten u fazu: {new_stage}', 'success')
    except Exception as e:
        flash(f'Greška: {str(e)}', 'danger')

    return redirect(url_for('customers.view', id=id))


@customers_bp.route('/<int:id>/add-note', methods=['POST'])
@login_required
def add_note(id):
    """Add note to customer."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_view_customer(customer):
        flash('Nemate dozvolu za pristup ovom klijentu.', 'danger')
        return redirect(url_for('customers.index'))

    note = CustomerNote(
        customer_id=id,
        user_id=current_user.id,
        note_type=request.form.get('note_type', 'general'),
        subject=request.form.get('subject'),
        content=request.form.get('content'),
        is_important=request.form.get('is_important') == 'on'
    )

    db.session.add(note)

    # Update last contact date
    customer.last_contact_date = datetime.utcnow()

    db.session.commit()

    flash('Bilješka dodana.', 'success')
    return redirect(url_for('customers.view', id=id))


@customers_bp.route('/<int:id>/log-activity', methods=['POST'])
@login_required
def log_activity(id):
    """Log activity with customer."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_view_customer(customer):
        flash('Nemate dozvolu za pristup ovom klijentu.', 'danger')
        return redirect(url_for('customers.index'))

    activity = Activity(
        customer_id=id,
        user_id=current_user.id,
        activity_type=ActivityType[request.form.get('activity_type', 'NOTE')],
        subject=request.form.get('subject'),
        description=request.form.get('description'),
        activity_date=datetime.utcnow(),
        outcome=request.form.get('outcome')
    )

    db.session.add(activity)

    # Update last contact date
    customer.last_contact_date = datetime.utcnow()

    db.session.commit()

    flash('Aktivnost zabilježena.', 'success')
    return redirect(url_for('customers.view', id=id))


@customers_bp.route('/api/qualification-score/<int:id>', methods=['POST'])
@login_required
def calculate_qualification_score(id):
    """Calculate and update customer qualification score."""
    customer = Customer.query.get_or_404(id)

    if not AccessControl.can_edit_customer(customer):
        return jsonify({'error': 'Access denied'}), 403

    score = customer.calculate_qualification_score()
    db.session.commit()

    return jsonify({'score': score})
