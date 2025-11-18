"""Activity and task management blueprint."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.models.activity import Activity, Task, Meeting, ActivityType, TaskStatus, TaskPriority
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.user import User
from app.utils.decorators import audit_action
from app.utils.query_filters import apply_task_filter, apply_customer_filter
from app.utils.access_control import AccessControl

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')


@activities_bp.route('/tasks')
@login_required
def tasks():
    """List tasks with filtering."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    view = request.args.get('view', 'my')  # 'my' or 'team'

    # Base query with access control
    query = apply_task_filter(Task.query)

    # View filter
    if view == 'my':
        query = query.filter(Task.assigned_to_id == current_user.id)

    # Apply filters
    if status:
        try:
            query = query.filter_by(status=TaskStatus[status.upper()])
        except KeyError:
            pass

    if priority:
        try:
            query = query.filter_by(priority=TaskPriority[priority.upper()])
        except KeyError:
            pass

    # Check for overdue tasks
    for task in query.filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])).all():
        task.check_overdue()
    db.session.commit()

    # Order by due date
    query = query.order_by(Task.due_date.asc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    tasks = pagination.items

    return render_template('activities/tasks.html',
                         tasks=tasks,
                         pagination=pagination,
                         statuses=TaskStatus,
                         priorities=TaskPriority,
                         current_status=status,
                         current_priority=priority,
                         current_view=view)


@activities_bp.route('/tasks/<int:id>')
@login_required
@audit_action('view', 'task')
def view_task(id):
    """View task details."""
    task = apply_task_filter(Task.query).filter_by(id=id).first_or_404()

    return render_template('activities/task_view.html', task=task)


@activities_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
@audit_action('create', 'task')
def create_task():
    """Create new task."""
    if request.method == 'POST':
        # Parse due date
        due_date_str = request.form.get('due_date')
        due_time_str = request.form.get('due_time', '23:59')
        due_datetime = datetime.strptime(f'{due_date_str} {due_time_str}', '%Y-%m-%d %H:%M')

        task = Task(
            title=request.form.get('title'),
            description=request.form.get('description'),
            priority=TaskPriority[request.form.get('priority', 'MEDIUM')],
            task_type=request.form.get('task_type'),
            assigned_to_id=request.form.get('assigned_to_id', type=int),
            assigned_by_id=current_user.id,
            due_date=due_datetime,
            customer_id=request.form.get('customer_id', type=int) or None,
            opportunity_id=request.form.get('opportunity_id', type=int) or None
        )

        # Calculate SLA deadline if SLA hours provided
        sla_hours = request.form.get('sla_hours', type=int)
        if sla_hours:
            task.sla_hours = sla_hours
            task.sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

        db.session.add(task)
        db.session.commit()

        flash('Zadatak uspješno kreiran.', 'success')
        return redirect(url_for('activities.view_task', id=task.id))

    # Get accessible users for assignment
    accessible_user_ids = AccessControl.get_accessible_user_ids()
    users = User.query.filter(User.id.in_(accessible_user_ids)).order_by(User.last_name).all()

    # Get customers for linking
    customers = apply_customer_filter(Customer.query).order_by(Customer.last_name).limit(100).all()

    return render_template('activities/task_create.html',
                         users=users,
                         customers=customers,
                         priorities=TaskPriority)


@activities_bp.route('/tasks/<int:id>/complete', methods=['POST'])
@login_required
@audit_action('complete', 'task')
def complete_task(id):
    """Mark task as completed."""
    task = apply_task_filter(Task.query).filter_by(id=id).first_or_404()

    if task.assigned_to_id != current_user.id:
        flash('Možete završiti samo svoje zadatke.', 'danger')
        return redirect(url_for('activities.view_task', id=id))

    task.complete()
    db.session.commit()

    flash('Zadatak završen.', 'success')
    return redirect(url_for('activities.tasks'))


@activities_bp.route('/tasks/<int:id>/escalate', methods=['POST'])
@login_required
@audit_action('escalate', 'task')
def escalate_task(id):
    """Escalate task to higher level."""
    task = apply_task_filter(Task.query).filter_by(id=id).first_or_404()

    escalate_to_id = request.form.get('escalate_to_id', type=int)
    if not escalate_to_id:
        flash('Odaberite korisnika za eskalaciju.', 'danger')
        return redirect(url_for('activities.view_task', id=id))

    task.escalate(escalate_to_id)
    db.session.commit()

    flash('Zadatak eskaliran.', 'info')
    return redirect(url_for('activities.view_task', id=id))


@activities_bp.route('/meetings')
@login_required
def meetings():
    """List meetings."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    view = request.args.get('view', 'upcoming')  # 'upcoming', 'past', 'all'

    query = Meeting.query

    # View filter
    now = datetime.utcnow()
    if view == 'upcoming':
        query = query.filter(Meeting.start_time >= now, Meeting.status == 'scheduled')
    elif view == 'past':
        query = query.filter(Meeting.start_time < now)

    # Only show meetings user is involved in or can access
    if current_user.access_level.value > 2:  # Individual and Branch level
        query = query.filter(Meeting.organizer_id == current_user.id)

    # Order by start time
    if view == 'past':
        query = query.order_by(Meeting.start_time.desc())
    else:
        query = query.order_by(Meeting.start_time.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    meetings = pagination.items

    return render_template('activities/meetings.html',
                         meetings=meetings,
                         pagination=pagination,
                         current_view=view)


@activities_bp.route('/meetings/<int:id>')
@login_required
@audit_action('view', 'meeting')
def view_meeting(id):
    """View meeting details."""
    meeting = Meeting.query.get_or_404(id)

    return render_template('activities/meeting_view.html', meeting=meeting)


@activities_bp.route('/meetings/create', methods=['GET', 'POST'])
@login_required
@audit_action('create', 'meeting')
def create_meeting():
    """Create new meeting."""
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        start_datetime = datetime.strptime(f'{start_date_str} {start_time_str}', '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(f'{start_date_str} {end_time_str}', '%Y-%m-%d %H:%M')

        meeting = Meeting(
            title=request.form.get('title'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            meeting_url=request.form.get('meeting_url'),
            start_time=start_datetime,
            end_time=end_datetime,
            organizer_id=current_user.id,
            customer_id=request.form.get('customer_id', type=int) or None,
            opportunity_id=request.form.get('opportunity_id', type=int) or None,
            agenda=request.form.get('agenda')
        )

        # Generate pre-meeting briefing if customer is linked
        if meeting.customer_id:
            meeting.generate_pre_meeting_briefing()

        db.session.add(meeting)
        db.session.commit()

        flash('Sastanak uspješno kreiran.', 'success')
        return redirect(url_for('activities.view_meeting', id=meeting.id))

    customers = apply_customer_filter(Customer.query).order_by(Customer.last_name).limit(100).all()

    return render_template('activities/meeting_create.html', customers=customers)


@activities_bp.route('/calendar')
@login_required
def calendar():
    """Calendar view of meetings and tasks."""
    # Get meetings and tasks for current month
    month = request.args.get('month', datetime.utcnow().month, type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    meetings = Meeting.query.filter(
        Meeting.start_time >= start_date,
        Meeting.start_time < end_date,
        Meeting.organizer_id == current_user.id
    ).all()

    tasks = apply_task_filter(Task.query).filter(
        Task.due_date >= start_date,
        Task.due_date < end_date,
        Task.assigned_to_id == current_user.id
    ).all()

    return render_template('activities/calendar.html',
                         meetings=meetings,
                         tasks=tasks,
                         month=month,
                         year=year)
