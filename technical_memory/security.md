# Technical Memory: Security Controls

## 1. Access Control
*   **Signatures**: API access uses JWT validation signed with a server-level HS256 secret.
*   **Decoupled Authentication**: User passwords are encrypted with bcrypt inside the DB adapter layer.

## 2. Secure Execution Rules
*   **SQL Injection**: Enforced strictly by using SQLAlchemy's parameterized expression engine instead of raw SQL strings.
*   **Content Security Policy (CSP)**: Handled at the Nginx reverse-proxy layer to restrict script injections.
