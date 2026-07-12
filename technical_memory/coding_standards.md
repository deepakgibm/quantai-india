# Technical Memory: Coding Standards

## 1. Naming Conventions
*   **Python**: Use `snake_case` for all function names, variables, and files. Use `PascalCase` for classes.
*   **React/TypeScript**: Use `PascalCase` for component files and React components. Use `camelCase` for variables, hook names, and utilities.

## 2. Coding Rules
*   **Centralized Price Resolution**: All spot price lookups must use the central `PriceService` (`backend/services/price_manager/price_service.py`).
*   **Upstox-Only Live Data**: Never mock or simulate market feeds in production.
*   **Structured Sessions**: Ensure all database queries utilize standard session builders and cleanly terminate sessions inside `finally` blocks.
