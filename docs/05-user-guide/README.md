# User Guides

This directory contains user-facing documentation for working with the Backcast  system.

## Available Guides

### [Change Order Workflow & Architecture Guide](./change-order-workflow-guide.md)

Comprehensive documentation of the Change Order workflow and backend logic.

**Topics Covered:**
- Entity model and relationships
- Workflow state machine and transitions
- Branch isolation and merge operations
- Impact analysis and approval matrix
- API endpoints and usage examples
- Debugging common issues

**Target Audience:**
- Backend developers working with change orders
- System administrators debugging workflow issues
- Technical users understanding the approval process

### [EVCS User Guide: Working with Versioned Entities](./evcs-wbs-element-user-guide.md)

A comprehensive guide to the Entity Versioning Control System (EVCS) using the WBS Element entity as the primary example.

**Topics Covered:**
- Basic CRUD operations with versioning
- Version history and time travel queries
- Control date operations for retroactive changes
- Branching for change order workflows
- Hierarchical WBS Element management
- Revert operations
- API reference
- Best practices and common patterns

**Target Audience:**
- Backend developers integrating with the API
- System architects designing EVCS-based features
- QA engineers writing tests for versioned entities

### [Docker Deployment Guide](./docker-deployment-guide.md)

Production deployment guide using Docker, Traefik, and Let's Encrypt SSL.

**Topics Covered:**
- Prerequisites and server requirements
- Architecture overview
- Step-by-step deployment instructions
- SSL/TLS configuration
- Troubleshooting common issues
- Maintenance and updates

**Target Audience:**
- DevOps engineers
- System administrators
- Developers deploying to staging/production

### [AI Chat User Guide](./ai-chat-user-guide.md)

End-user guide for interacting with the Backcast  AI Chat assistant using natural language.

**Topics Covered:**
- Getting started with AI Chat
- Project information queries (list, search, filter)
- Work Breakdown Structure (WBE) navigation and hierarchy
- Cost element analysis and variance tracking
- Change order draft generation and workflow
- Earned Value Management (EVM) metrics and forecasting
- Tips for better results and troubleshooting

**Target Audience:**
- Project managers using AI for project insights
- Cost engineers performing analysis
- Change managers managing change orders
- Any end user interacting with the AI assistant

### [Notification System User Guide](./notification-system-guide.md)

End-user and administrator guide for Backcast's unified, real-time notification system (in-app bell + Notification Center + Telegram).

**Topics Covered:**
- Notification categories, severities, and actors
- The bell, Notification Center, and real-time delivery
- Use cases: change-order approvals, background agents, Telegram while away, catching up after being offline
- Managing per-category/per-channel preferences
- Connecting Telegram (deep-link flow)
- Administrator setup (env vars, webhook vs polling, admin chat)
- Troubleshooting

**Target Audience:**
- All Backcast users receiving or acting on notifications
- Approvers and change managers
- Anyone running background AI agents
- Administrators enabling Telegram delivery

### [Configuring Backcast for Your Organization](./backcast-configuration-guide.md)

Adaptation guide for administrators covering roles, workflows, AI assistance, and team structure configuration.

**Topics Covered:**
- Organizational role configuration and delegation styles (centralized, balanced, distributed)
- Change management workflow configuration (lean, formal CCB, enterprise governance)
- AI assistant persona selection, customization, and maturity-based deployment
- Execution safety tiers and role-matching guidelines
- Quick-reference matrix by team size (solo to enterprise)
- Step-by-step configuration checklist

**Target Audience:**
- System administrators deploying Backcast
- PMO directors defining governance policies
- IT leads managing user accounts and security

### [Frontend Navigation Patterns](./navigation-patterns.md)

Guide to the navigation patterns used in the Backcast  frontend application.

**Topics Covered:**

- URL-driven navigation approach
- PageNavigation component usage
- Nested routing pattern for entities
- When to use contextual navigation
- Best practices and examples

**Target Audience:**

- Frontend developers
- UI/UX designers
- Contributors working on navigation features

### [Human-AI Collaboration Guide](./human-ai-collaboration-guide.md)

A corporate-facing guide explaining how human project team members and AI assistants collaborate throughout the industrial automation project lifecycle — from order acquisition through commissioning.

**Topics Covered:**
- Organizational roles and responsibilities (PMI-aligned)
- AI assistant capabilities and boundaries
- Phase-by-phase collaboration guide with concrete examples
- Change management and governance (CCB process, tiered approval)
- Earned Value Management integration
- Corporate tool landscape coordination (ERP, CAD, scheduling, DMS)
- Best practices for human-AI collaboration
- RACI matrix template

**Target Audience:**
- Executives and PMO Directors evaluating Backcast
- Project Managers and Department Heads planning deployment
- Project Controllers and Cost Engineers
- External stakeholders and client organizations

### [Frontend Navigation Patterns](./navigation-patterns.md)

- [Architecture Documentation](../02-architecture/) - System design and architecture
- [Product Scope](../01-product-scope/) - Feature requirements and vision
- [Project Plan](../03-project-plan/) - Current iteration and sprint plans

## Contributing

When adding new user guides:

1. Use clear, practical examples
2. Include diagrams (Mermaid format) for visual concepts
3. Provide code snippets from actual tests where possible
4. Cross-reference related architecture documents
5. Include troubleshooting sections for common issues
