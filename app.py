"""Universal Bank CRM Application Entry Point."""
import os
from app import create_app, db
from app.models import (
    User, Role, AccessLevel, OrganizationalUnit,
    Customer, CustomerStage, CustomerSegment, CustomerNote,
    Opportunity, OpportunityStage, ProductLine,
    Activity, Task, Meeting,
    Target, TargetAchievement,
    AuditLog
)

# Create Flask app
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell."""
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'AccessLevel': AccessLevel,
        'OrganizationalUnit': OrganizationalUnit,
        'Customer': Customer,
        'CustomerStage': CustomerStage,
        'CustomerSegment': CustomerSegment,
        'CustomerNote': CustomerNote,
        'Opportunity': Opportunity,
        'OpportunityStage': OpportunityStage,
        'ProductLine': ProductLine,
        'Activity': Activity,
        'Task': Task,
        'Meeting': Meeting,
        'Target': Target,
        'TargetAchievement': TargetAchievement,
        'AuditLog': AuditLog
    }


@app.cli.command()
def init_db():
    """Initialize the database."""
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")


@app.cli.command()
def seed_db():
    """Seed database with sample data."""
    from datetime import datetime, timedelta

    print("Seeding database with sample data...")

    # Create organizational units
    bank = OrganizationalUnit(
        name='Universal Bank',
        type='division',
        code='UB',
        is_active=True
    )
    db.session.add(bank)
    db.session.flush()

    region_sarajevo = OrganizationalUnit(
        name='Sarajevo Region',
        type='region',
        code='SAR',
        parent_id=bank.id,
        is_active=True
    )
    db.session.add(region_sarajevo)
    db.session.flush()

    branch_centar = OrganizationalUnit(
        name='Centar Branch',
        type='branch',
        code='SAR-CNT',
        parent_id=region_sarajevo.id,
        is_active=True
    )
    db.session.add(branch_centar)
    db.session.flush()

    # Create users
    # Executive
    admin = User(
        username='admin',
        email='admin@universalbank.ba',
        first_name='Admin',
        last_name='User',
        access_level=AccessLevel.EXECUTIVE,
        role=Role.ADMIN,
        organizational_unit_id=bank.id,
        is_active=True,
        is_verified=True
    )
    admin.set_password('admin123')
    db.session.add(admin)

    # Regional Manager
    regional_mgr = User(
        username='regional',
        email='regional@universalbank.ba',
        first_name='Amir',
        last_name='Kovačević',
        access_level=AccessLevel.REGIONAL,
        role=Role.MANAGER,
        organizational_unit_id=region_sarajevo.id,
        is_active=True,
        is_verified=True
    )
    regional_mgr.set_password('regional123')
    db.session.add(regional_mgr)

    # Branch Manager
    branch_mgr = User(
        username='branch',
        email='branch@universalbank.ba',
        first_name='Selma',
        last_name='Hadžić',
        access_level=AccessLevel.BRANCH,
        role=Role.MANAGER,
        organizational_unit_id=branch_centar.id,
        is_active=True,
        is_verified=True
    )
    branch_mgr.set_password('branch123')
    db.session.add(branch_mgr)

    # Relationship Manager
    rm1 = User(
        username='rm1',
        email='rm1@universalbank.ba',
        first_name='Marko',
        last_name='Petrović',
        access_level=AccessLevel.INDIVIDUAL,
        role=Role.SALES,
        organizational_unit_id=branch_centar.id,
        is_active=True,
        is_verified=True
    )
    rm1.set_password('rm123')
    db.session.add(rm1)

    db.session.commit()

    # Create sample customers
    customers_data = [
        ('Emir', 'Bašić', CustomerStage.CUSTOMER, CustomerSegment.RETAIL, rm1.id),
        ('Ana', 'Marić', CustomerStage.LEAD, CustomerSegment.RETAIL, rm1.id),
        ('Dino', 'Hadžiahmetović', CustomerStage.PROSPECT, CustomerSegment.SME, rm1.id),
        ('', '', CustomerStage.SUSPECT, CustomerSegment.CORPORATE, rm1.id),
    ]

    customers_data[3] = ('Tech Solutions d.o.o.', '', CustomerStage.SUSPECT, CustomerSegment.CORPORATE, rm1.id)

    for first_name, last_name, stage, segment, owner_id in customers_data:
        customer = Customer(
            first_name=first_name,
            last_name=last_name,
            company_name=first_name if segment == CustomerSegment.CORPORATE else None,
            email=f"{first_name.lower().replace(' ', '')}@email.ba" if first_name else None,
            phone='+387 33 123 456',
            city='Sarajevo',
            country='BA',
            stage=stage,
            segment=segment,
            owner_id=owner_id,
            organizational_unit_id=branch_centar.id,
            suspect_date=datetime.utcnow() - timedelta(days=30),
            qualification_score=50
        )

        if stage == CustomerStage.CUSTOMER:
            customer.customer_date = datetime.utcnow() - timedelta(days=10)

        db.session.add(customer)

    db.session.flush()

    # Create sample opportunities
    customers = Customer.query.all()
    if len(customers) >= 2:
        opp1 = Opportunity(
            name='Stambeni kredit',
            description='Kredit za kupovinu stana',
            customer_id=customers[0].id,
            product_line=ProductLine.MORTGAGE,
            stage=OpportunityStage.PROPOSAL,
            amount=150000,
            probability=60,
            expected_close_date=datetime.utcnow().date() + timedelta(days=30),
            owner_id=rm1.id,
            organizational_unit_id=branch_centar.id,
            is_active=True
        )
        opp1.update_expected_revenue()
        db.session.add(opp1)

        opp2 = Opportunity(
            name='Kreditna kartica',
            description='Premium kreditna kartica',
            customer_id=customers[1].id,
            product_line=ProductLine.CREDIT_CARD,
            stage=OpportunityStage.NEGOTIATION,
            amount=5000,
            probability=75,
            expected_close_date=datetime.utcnow().date() + timedelta(days=15),
            owner_id=rm1.id,
            organizational_unit_id=branch_centar.id,
            is_active=True
        )
        opp2.update_expected_revenue()
        db.session.add(opp2)

    # Create sample tasks
    task1 = Task(
        title='Kontaktirati klijenta',
        description='Poslati email sa ponudom',
        priority='medium',
        status='pending',
        assigned_to_id=rm1.id,
        assigned_by_id=branch_mgr.id,
        due_date=datetime.utcnow() + timedelta(days=2)
    )
    db.session.add(task1)

    # Create sample target
    target = Target(
        name='Mjesečni cilj - Krediti',
        description='Mjesečni cilj za kredite',
        target_type='revenue',
        period_type='monthly',
        start_date=datetime.utcnow().date().replace(day=1),
        end_date=datetime.utcnow().date().replace(day=28),
        target_value=500000,
        achieved_value=150000,
        user_id=rm1.id,
        is_active=True
    )
    target.calculate_achievement()
    db.session.add(target)

    db.session.commit()

    print("Sample data created successfully!")
    print("\nLogin credentials:")
    print("  Executive:  admin / admin123")
    print("  Regional:   regional / regional123")
    print("  Branch:     branch / branch123")
    print("  RM:         rm1 / rm123")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
