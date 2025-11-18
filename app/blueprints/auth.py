"""Authentication blueprint."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from app import db, login_manager
from app.models.user import User
from app.models.audit import AuditLog

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            AuditLog.log_action(
                user=None,
                action='login_failed',
                resource_type='auth',
                description=f'Failed login attempt for username: {username}',
                success=False
            )
            flash('Neispravno korisničko ime ili lozinka.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Vaš nalog je deaktiviran. Kontaktirajte administratora.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()

        AuditLog.log_action(
            user=user,
            action='login',
            resource_type='auth',
            description='User logged in successfully'
        )

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')

        flash(f'Dobrodošli, {user.full_name}!', 'success')
        return redirect(next_page)

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    AuditLog.log_action(
        user=current_user,
        action='logout',
        resource_type='auth',
        description='User logged out'
    )

    logout_user()
    flash('Uspješno ste se odjavili.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile view."""
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_user.check_password(current_password):
            flash('Trenutna lozinka nije ispravna.', 'danger')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('Nove lozinke se ne podudaraju.', 'danger')
            return redirect(url_for('auth.change_password'))

        if len(new_password) < 8:
            flash('Lozinka mora imati najmanje 8 karaktera.', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.set_password(new_password)
        db.session.commit()

        AuditLog.log_action(
            user=current_user,
            action='password_change',
            resource_type='auth',
            description='User changed password'
        )

        flash('Lozinka uspješno promijenjena.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html')


@auth_bp.route('/change-language/<language>')
@login_required
def change_language(language):
    """Change user language preference."""
    if language not in ['bs', 'en', 'tr']:
        flash('Nevažeći jezik.', 'danger')
        return redirect(url_for('auth.profile'))

    # Update user's language preference
    current_user.language = language
    db.session.commit()

    # Also update session for immediate effect
    session['language'] = language

    flash_messages = {
        'bs': 'Jezik uspješno promijenjen.',
        'en': 'Language changed successfully.',
        'tr': 'Dil başarıyla değiştirildi.'
    }

    flash(flash_messages.get(language, 'Language changed.'), 'success')
    return redirect(url_for('auth.profile'))
