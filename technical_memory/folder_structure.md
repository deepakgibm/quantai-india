# Technical Memory: Folder Structure

This file maps repository folders to their active responsibilities.

---

## 📁 Directory Tree

```text
quantai-india/
├── backend/                  # Python backend application
│   ├── api/                  # FastAPI routers and controllers
│   ├── core/                 # Observability middlewares and settings
│   ├── database/             # SQLAlchemy schemas and DB connection
│   ├── services/             # Core logic services
│   │   ├── price_manager/    # Central PriceService engine
│   │   └── scanners/         # Scanning strategies
│   └── tests/                # Pytest suites
├── frontend/                 # React web application
│   ├── src/
│   │   ├── components/       # Shared React widgets
│   │   ├── pages/            # View pages (Dashboard, Scanner, Heatmap)
│   │   └── services/         # REST/WS gateways
├── docs/                     # Consolidated documentation subfolders
├── technical_memory/         # AI persistent project knowledge base
└── review_to_delete/         # Safely segregated legacy scripts
```
