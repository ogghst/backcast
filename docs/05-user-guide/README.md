# User Guides

This directory contains user-facing documentation for working with the Backcast EVS system.

## Available Guides

### [EVCS User Guide: Working with Versioned Entities](./evcs-wbe-user-guide.md)

A comprehensive guide to the Entity Versioning Control System (EVCS) using the WBE (Work Breakdown Element) entity as the primary example.

**Topics Covered:**
- Basic CRUD operations with versioning
- Version history and time travel queries
- Control date operations for retroactive changes
- Branching for change order workflows
- Hierarchical WBE management
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

### [Frontend Navigation Patterns](./navigation-patterns.md)

Guide to the navigation patterns used in the Backcast EVS frontend application.

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

## Additional Resources

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
