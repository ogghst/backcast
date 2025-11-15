# PESTA - Project Earned value Simulator, Time traveller and Analyzer

## High-Level Goal

PESTA is a comprehensive application designed for the Project Management Directorate to simulate, test, and validate financial management processes for end-of-line automation projects before implementing them in production environments.

The system enables organizations to:

- Model complex project scenarios with multiple machines (WBEs) and departmental cost elements
- Track project financial performance using Earned Value Management (EVM) principles
- Validate business rules and performance metrics under various conditions
- Support complete project lifecycle financial management including budgets, costs, forecasts, change orders, and quality events
- Generate accurate EVM calculations and reports for decision-making

This tool serves as a simulation and validation platform, allowing the Project Management Directorate to refine business rules, test performance metrics, and establish best practices for project financial management without impacting production systems.

## Documentation Structure

All project documentation is located in the [`docs/`](docs/) directory:

### Core Documentation

- **[`prd.md`](docs/prd.md)** - Product Requirements Document
  - Comprehensive requirements specification
  - Business context and objectives
  - System capabilities and features
  - EVM calculation requirements
  - User interface and reporting requirements

- **[`plan.md`](docs/plan.md)** - Project Plan and MVP Development Roadmap
  - Executive summary and development approach
  - Epic breakdown (5 major epics)
  - Sprint plan overview (6 two-week sprints)
  - MVP scope definition
  - Resource requirements and success criteria

- **[`data_model.md`](docs/data_model.md)** - Data Model Documentation
  - Entity relationships and data structure
  - Database schema definitions
  - Data validation rules

- **[`project_status.md`](docs/project_status.md)** - Project Status
  - Current development status
  - Progress tracking and milestones

## Project Structure

```text
/
├── docs/                    # Project documentation
│   ├── prd.md              # Product Requirements Document
│   ├── plan.md             # Project plan and roadmap
│   ├── data_model.md       # Data model documentation
│   └── project_status.md   # Current project status
├── frontend/              # Frontend app
├── backend/              # Backend app
└── README.md               # This file
```

## Key Features

The MVP will support:

- **Project Structure Management**: Create and manage projects, Work Breakdown Elements (WBEs), and cost elements
- **Budget & Revenue Management**: Allocate budgets and revenues, create time-phased plans
- **Cost Recording**: Register actual costs and track expenditures
- **Earned Value Tracking**: Record work completion and calculate EVM metrics
- **Forecasting**: Create and update estimates at completion (EAC)
- **Change Order Management**: Process scope changes and contract modifications
- **EVM Calculations**: Automatic calculation of CPI, SPI, variances, and performance indices
- **Reporting & Dashboards**: Generate standard EVM reports and performance visualizations

## Development Status

This project follows an agile development methodology with a planned 12-week MVP timeline organized into six two-week sprints. See [`docs/plan.md`](docs/plan.md) for detailed sprint breakdowns and [`docs/project_status.md`](docs/project_status.md) for current status.


## Technology Stack and Features

- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API.
    - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
    - 🔍 [Pydantic](https://docs.pydantic.dev), used by FastAPI, for the data validation and settings management.
    - 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
- 🚀 [React](https://react.dev) for the frontend.
    - 💃 Using TypeScript, hooks, Vite, and other parts of a modern frontend stack.
    - 🎨 [Chakra UI](https://chakra-ui.com) for the frontend components.
    - 🤖 An automatically generated frontend client.
    - 🧪 [Playwright](https://playwright.dev) for End-to-End testing.
    - 🦇 Dark mode support.
- 🐋 [Docker Compose](https://www.docker.com) for development and production.
- 🔒 Secure password hashing by default.
- 🔑 JWT (JSON Web Token) authentication.
- 📫 Email based password recovery.
- ✅ Tests with [Pytest](https://pytest.org).
- 📞 [Traefik](https://traefik.io) as a reverse proxy / load balancer.
- 🚢 Deployment instructions using Docker Compose, including how to set up a frontend Traefik proxy to handle automatic HTTPS certificates.
- 🏭 CI (continuous integration) and CD (continuous deployment) based on GitHub Actions.

## How To Use It

You can **just fork or clone** this repository and use it as is.

✨ It just works. ✨

### Configure

You can then update configs in the `.env` files to customize your configurations.

Before deploying it, make sure you change at least the values for:

- `SECRET_KEY`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`

You can (and should) pass these as environment variables from secrets.

Read the [deployment.md](./deployment.md) docs for more details.

### Generate Secret Keys

Some environment variables in the `.env` file have a default value of `changethis`.

You have to change them with a secret key, to generate secret keys you can run the following command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the content and use that as password / secret key. And run that again to generate another secure key.

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Frontend Development

Frontend docs: [frontend/README.md](./frontend/README.md).

## Deployment

Deployment docs: [deployment.md](./deployment.md).

## Development

General development docs: [development.md](./development.md).

This includes using Docker Compose, custom local domains, `.env` configurations, etc.

## License

See [LICENSE](LICENSE) file for license information.
