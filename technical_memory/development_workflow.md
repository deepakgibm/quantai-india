# Technical Memory: Development Workflow

## 1. Local Environment Setup

To start the platform locally, spin up the Docker Compose stack:
```bash
docker-compose up -d --build
```

## 2. Code Review & PR Checklist
Before merging changes to the repository:
1.  Verify that all Python tests pass: `pytest tests/`
2.  Confirm that the frontend compiles cleanly: `npm run build`
3.  Ensure database indexes exist for any new query columns.
