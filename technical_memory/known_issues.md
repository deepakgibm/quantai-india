# Technical Memory: Known Issues & Technical Debt

## 1. Active Tech Debt
*   **Deprecation Warnings**: FastAPI `on_event` startup and shutdown handlers need migration to the modern async `lifespan` context manager.
*   **Protobuf Deprecations**: `FieldDescriptor` calls in `backend/utils/upstox_proto.py` raise warnings on unlinked descriptors under Python 3.11/protobuf updates.

## 2. Deferred Refactoring
*   **Celery Bloat**: Long-running Celery processes require monitoring to prevent memory fragmentation on Docker workers.
