# Universal Bank CRM

A comprehensive CRM system for Universal Bank built with Flask, featuring a hierarchical 4-layer access control system, customer lifecycle management, opportunity tracking, and analytics.

## Features

### Core Functionality

- **Customer Lifecycle Management**: Suspect → Prospect → Lead → Customer pipeline with qualification scoring
- **Opportunity/Deal Management**: Product-specific pipelines with stage tracking and revenue forecasting
- **Activity & Task Management**: Meeting scheduling, task tracking with SLA monitoring, and escalation
- **Target Management**: Hierarchical target allocation with real-time achievement tracking
- **Analytics & Reporting**: Dashboard with KPIs, conversion rates, pipeline analytics, and team performance
- **4-Layer Access Control**: Executive, Regional, Branch, and Individual levels with data isolation

### Security Features

- Role-based access control (RBAC)
- Hierarchical organizational unit access
- Data masking for sensitive information
- Complete audit logging for compliance
- Session management and authentication

### Technical Features

- Modern, responsive UI with Tailwind CSS
- RESTful API endpoints
- Comprehensive logging and monitoring
- Database migrations with Flask-Migrate
- Modular blueprint architecture

## Technology Stack

- **Backend**: Flask 3.0
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Frontend**: Tailwind CSS 3.x
- **Forms**: Flask-WTF

## Project Structure

```
crm_ub/
├── app/
│   ├── __init__.py              # Application factory
│   ├── blueprints/              # Route blueprints
│   │   ├── auth.py              # Authentication
│   │   ├── main.py              # Dashboard
│   │   ├── customers.py         # Customer management
│   │   ├── opportunities.py     # Deal management
│   │   ├── activities.py        # Tasks & meetings
│   │   ├── targets.py           # Target management
│   │   └── analytics.py         # Reporting
│   ├── models/                  # Database models
│   │   ├── user.py              # Users & access control
│   │   ├── customer.py          # Customer lifecycle
│   │   ├── opportunity.py       # Opportunities
│   │   ├── activity.py          # Activities & tasks
│   │   ├── target.py            # Targets
│   │   └── audit.py             # Audit logging
│   ├── templates/               # Jinja2 templates
│   │   ├── layouts/             # Base templates
│   │   ├── auth/                # Authentication pages
│   │   ├── customers/           # Customer pages
│   │   ├── opportunities/       # Opportunity pages
│   │   ├── activities/          # Activity pages
│   │   ├── targets/             # Target pages
│   │   ├── dashboard/           # Dashboard
│   │   ├── analytics/           # Analytics
│   │   └── errors/              # Error pages
│   └── utils/                   # Utilities
│       ├── decorators.py        # Security decorators
│       ├── access_control.py    # Access control helpers
│       └── query_filters.py     # Query filtering
├── logs/                        # Application logs
├── instance/                    # Instance-specific files
├── app.py                       # Application entry point
├── config.py                    # Configuration
├── requirements.txt             # Python dependencies
├── CLAUDE.md                    # Claude Code guidance
└── ub_spec.txt                  # Business specification

```

## Installation & Setup

### Prerequisites

- Python 3.9+
- pip
- virtualenv (recommended)

### Installation Steps

1. **Clone or navigate to the repository**
   ```bash
   cd /srv/crm_ub
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables (optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize the database**
   ```bash
   flask init-db
   ```

6. **Seed with sample data**
   ```bash
   flask seed-db
   ```

7. **Run the application**
   ```bash
   python app.py
   # Or: flask run --host=0.0.0.0 --port=5000
   ```

8. **Access the application**
   - Open browser to: http://localhost:5000
   - Default login credentials (see below)

## Default Login Credentials

After seeding the database, use these credentials:

| Role | Username | Password | Access Level |
|------|----------|----------|--------------|
| Executive | admin | admin123 | Full system access |
| Regional Manager | regional | regional123 | Regional data access |
| Branch Manager | branch | branch123 | Branch data access |
| Relationship Manager | rm1 | rm123 | Own portfolio only |

**⚠️ IMPORTANT**: Change these passwords immediately in production!

## Configuration

The application uses environment-based configuration:

- `development`: Debug mode, verbose logging
- `production`: Optimized for production use
- `testing`: For unit tests

Set the environment:
```bash
export FLASK_ENV=production  # or development, testing
```

## 4-Layer Access Control Model

### Layer 1: Executive (C-Suite)
- Full system access
- Bank-wide analytics
- All organizational units

### Layer 2: Regional/Divisional Management
- Regional/divisional data access
- Team performance monitoring
- Target setting for region

### Layer 3: Branch/Team Managers
- Branch/team customer portfolios
- Individual team member activities
- Local pipeline management
- Cannot access other branches without permission

### Layer 4: Relationship Managers/Sales Staff
- Own customer portfolio only
- Assigned leads and prospects
- Personal tasks and targets
- Limited reporting capabilities

## Database Migrations

When modifying models:

```bash
flask db init              # First time only
flask db migrate -m "Description of changes"
flask db upgrade
```

## Logging

Logs are written to:
- `logs/crm_ub.log` - Application logs
- `logs/audit.log` - Audit trail (compliance)

Log rotation is automatic (10MB max, 10 backups).

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Customers
- `GET /customers/` - List customers (filtered by access level)
- `GET /customers/<id>` - View customer details
- `POST /customers/create` - Create new customer
- `POST /customers/<id>/edit` - Update customer
- `POST /customers/<id>/advance-stage` - Move to next stage

### Opportunities
- `GET /opportunities/` - List opportunities
- `GET /opportunities/<id>` - View opportunity
- `POST /opportunities/create` - Create opportunity
- `POST /opportunities/<id>/mark-won` - Mark as won
- `POST /opportunities/<id>/mark-lost` - Mark as lost

### Analytics (Branch+ only)
- `GET /analytics/` - Analytics dashboard
- `GET /analytics/customers` - Customer analytics
- `GET /analytics/pipeline` - Pipeline analytics
- `GET /analytics/team-performance` - Team performance

## Development Commands

```bash
# Run in development mode
python app.py

# Enter Flask shell with models loaded
flask shell

# Initialize database
flask init-db

# Seed sample data
flask seed-db
```

## Localization

The application is configured for Bosnia & Herzegovina:
- Primary language: Bosnian/Croatian/Serbian (Latin)
- Timezone: Europe/Sarajevo
- Currency: BAM (Bosnian Convertible Mark)

## Security Considerations

1. **Sensitive Data**: High-net-worth customer data requires elevated access
2. **Audit Logging**: All data access is logged for compliance
3. **Data Masking**: Account numbers masked for non-privileged users
4. **Session Security**: HTTP-only cookies, CSRF protection
5. **Password Policy**: Minimum 8 characters (enhance as needed)

## Production Deployment

Before deploying to production:

1. Set `SECRET_KEY` environment variable
2. Configure production database (PostgreSQL recommended)
3. Set `FLASK_ENV=production`
4. Enable HTTPS
5. Configure reverse proxy (nginx/Apache)
6. Set up monitoring and backups
7. Review and update security settings

## Compliance Features

- **AML/KYC Status Tracking**: Customer compliance monitoring
- **Audit Logs**: Immutable audit trail for all operations
- **Data Retention**: Configurable retention policies
- **Consent Management**: GDPR/privacy compliance
- **Regulatory Reporting**: Banking agency compliance

## Support

For issues or questions, refer to:
- `CLAUDE.md` - Development guidance
- `ub_spec.txt` - Business requirements
- Application logs in `logs/` directory

## License

Proprietary - Universal Bank © 2024
