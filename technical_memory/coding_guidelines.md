# Technical Memory: Coding Guidelines

## 1. Feature Creation Checklist

When introducing a new scanner or stock metric feature, developers must adhere to the following sequence:

1.  **Define DTO/Model**: Add the necessary DB model in `backend/models.py` or create a Pydantic schema in `backend/schemas.py`.
2.  **Service Integration**: Implement business calculations inside a module in `backend/services/`. Import `PriceService` for quote resolution.
3.  **API Handler**: Create an endpoint router in `backend/api/`, registering it inside `backend/main.py`.
4.  **Frontend State**: Integrate API fetching inside `frontend/src/services/api.ts` and set Zustand keys.
5.  **Interactive Component**: Build the React page or widget under `frontend/src/pages/` or `frontend/src/components/`.

## 2. Refactoring Rules
*   Never write duplicate business logic.
*   Do not call external APIs (such as Upstox) directly from React frontend views.
