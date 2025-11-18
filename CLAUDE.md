# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive CRM system for Universal Bank (Bosnia & Herzegovina context). The system manages the complete customer lifecycle from suspect to customer, with sophisticated opportunity management, hierarchical access control, and integration with core banking systems.

**Current Status**: Specification phase - implementation not yet started. See `ub_spec.txt` for full requirements.

## Core Business Domains

### 1. Customer Lifecycle Management
- **Suspect → Prospect → Lead → Customer pipeline**
- Qualification scoring based on demographics, assets, creditworthiness
- Customer 360° view across all products and touchpoints
- Automated nurturing workflows by product line (retail, SME, corporate, private banking)

### 2. Opportunity & Deal Management
- Product-specific pipelines: loans, mortgages, investment products, business accounts
- Standard stages: Identification → Qualification → Proposal → Negotiation → Closing → Post-sale
- Deal scoring, probability tracking, and revenue forecasting
- Integrated approval workflows with credit/risk systems
- Cross-sell/up-sell opportunity identification

### 3. Hierarchical Access Control (4-Layer Model)
**Critical architectural requirement - must be enforced at data query level**

- **Layer 1 (C-Suite/Executive)**: Full system access, bank-wide analytics
- **Layer 2 (Regional/Divisional)**: Regional/divisional data, team performance monitoring
- **Layer 3 (Branch/Team Managers)**: Branch/team portfolios, cannot access other branches without permission
- **Layer 4 (Relationship Managers/Staff)**: Own customer portfolio and assigned leads only

Additional controls: role-based permissions, product-line restrictions, sensitive data masking, audit trails

### 4. Target Management
- Hierarchical target allocation: Branch → Team → Individual
- Product-wise and customer segment-wise targets
- Real-time achievement tracking with conversion rate analysis
- Dynamic redistribution based on performance
- Automated incentive calculation

## Integration Architecture

### Required External System Integrations
- **Core Banking System (CBS)**: Real-time account info, transactions, product holdings, credit facilities
- **Credit Scoring/Approval Systems**: Deal approval workflows
- **Document Management**: Customer documentation
- **Communication Platforms**: Email, SMS, WhatsApp
- **Marketing Automation**: Campaign management
- **Risk Management & Compliance**: KYC/AML status tracking

Design integration points with abstraction layers to support multiple CBS providers.

## Key Technical Requirements

### Multi-tenancy & Data Isolation
Implement strict data isolation between organizational units (branches, divisions) at the database query level. Access control must be enforced in data layer, not just UI.

### Activity & Task Management
- Calendar integration (Outlook/Google)
- Automated escalation for overdue tasks
- SLA tracking for customer commitments
- Pre-meeting briefings with customer history
- Automatic CRM updates from meeting notes

### Mobile Capabilities
- Offline functionality for field officers (critical for Bosnia & Herzegovina context)
- Quick customer onboarding
- Document capture and upload
- Location-based check-ins

### Analytics & AI Features
- Predictive: churn prediction, next-best-product recommendations, lifetime value calculation
- Lead scoring AI models
- Automated data entry from documents
- Meeting summaries generation
- Email/communication auto-classification

### Compliance & Audit
- Complete audit logs for all customer interactions and data access
- AML/KYC status tracking
- Customer consent management (GDPR/data privacy)
- Data retention policies
- Regulatory reporting for Banking Agency of Bosnia & Herzegovina

## Localization Requirements

- Multi-language support: Bosnian/Croatian/Serbian (Latin and Cyrillic), English
- Local regulatory compliance (Banking Agency requirements)
- Integration with local payment systems
- Consider branch-heavy vs. digital preferences in local context

## Architecture Considerations

When implementing this system, consider:

1. **Event-Driven Architecture**: Customer lifecycle transitions, deal stage changes, and target achievements should emit events for analytics and integrations
2. **CQRS Pattern**: Separate read models for different access control layers to optimize query performance
3. **Audit Logging**: Immutable audit log for all sensitive operations (regulatory requirement)
4. **Data Masking**: Field-level encryption for sensitive data with role-based decryption
5. **API-First Design**: All integrations through well-defined APIs for CBS, credit systems, etc.
6. **Workflow Engine**: Configurable workflows for deal approvals, lead nurturing, task escalation

## Security Guidelines

- Never expose complete account numbers in logs or non-production environments
- Implement row-level security for multi-tenant data isolation
- All sensitive operations must be audited with user identity, timestamp, and action
- API keys and credentials must never be committed to repository
- High-net-worth customer details require additional access controls beyond standard layer model
