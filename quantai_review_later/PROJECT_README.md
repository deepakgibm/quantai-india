#  QuantAI India - AI-Powered Trading Bot

> **Full-Stack Trading Platform with Upstox Integration & Google Gemini AI**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![Upstox](https://img.shields.io/badge/Upstox-Integrated-orange)](https://upstox.com/)

---

##  Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Screenshots](#screenshots)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

##  Features

###  Core Features
-  **Real-time Dashboard** - Live P&L, positions, and market overview
-  **AI Trading Assistant** - Powered by Google Gemini for strategy suggestions
-  **Upstox Integration** - Full broker integration for live trading
-  **Secure Authentication** - JWT-based user authentication
-  **Algorithm Management** - Create, test, and deploy trading algorithms
-  **Risk Management** - Advanced capital allocation and risk controls
-  **Responsive Design** - Works on desktop, tablet, and mobile
-  **Dark Mode** - Eye-friendly dark theme

###  Technical Features
- **Backend**: FastAPI with async SQLAlchemy
- **Frontend**: React + TypeScript + Vite
- **Database**: SQLite (upgradable to PostgreSQL)
- **Authentication**: JWT tokens with bcrypt hashing
- **AI**: Google Gemini API integration
- **Broker**: Upstox OAuth2 integration
- **Styling**: TailwindCSS with modern design

---

##  Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Upstox API credentials
- Google Gemini API key

### Installation

**1. Clone or navigate to the repository:**
```bash
cd quantai-india
```

**2. Install Dependencies:**

Backend:
```bash
cd backend
pip install -r requirements.txt
```

Frontend:
```bash
cd ..
npm install
```

**3. Configure Environment:**

Edit `backend/.env`:
```env
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_API_SECRET=your_upstox_api_secret
UPSTOX_REDIRECT_URI=http://localhost:5173/callback
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your-super-secret-key-change-this
```

**4. Start the Application:**

**Option A - Using the startup script (Recommended):**
```bash
start-app.bat
```

**Option B - Manual start:**

Terminal 1 (Backend):
```bash
cd backend
uvicorn main:app --reload
```

Terminal 2 (Frontend):
```bash
npm run dev
```

**5. Access the Application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

##  Architecture

```
quantai-india/

 frontend/                # React + TypeScript Frontend
    pages/              # Application pages
       Login.tsx
       Dashboard.tsx
       AIPrompt.tsx
       Orders.tsx
       AlgoBuilder.tsx
       LiveMonitor.tsx
       RiskManager.tsx
       Settings.tsx
   
    components/         # Reusable components
       Sidebar.tsx
   
    services/          # API integration
       api.ts
   
    types.ts           # TypeScript definitions
    App.tsx            # Main app component
    index.tsx          # Entry point

 backend/               # FastAPI Backend
    routers/          # API endpoints
       auth.py       # Authentication
       upstox.py     # Upstox integration
       trading.py    # Trading endpoints
       orders.py     # Order management
       ai.py         # AI features
       algorithms.py # Algorithm management
       risk.py       # Risk management
       settings.py   # User settings
   
    utils/            # Helper functions
       auth.py       # JWT & password utils
   
    main.py           # FastAPI application
    config.py         # Configuration
    database.py       # Database setup
    models.py         # SQLAlchemy models
    schemas.py        # Pydantic schemas
    .env              # Environment variables

 SETUP_GUIDE.md        # Detailed setup guide
 start-app.bat         # Quick start script
 package.json          # Node dependencies
```

---

##  Screenshots

### Dashboard
- Real-time P&L tracking
- Live market indices
- Active algorithms status
- Quick AI prompt access

### AI Trading Assistant
- Natural language trading queries
- Stock recommendations
- Strategy suggestions
- Market analysis

### Algorithm Builder
- Create custom strategies
- Backtest algorithms
- Monitor performance
- Activate/deactivate bots

### Live Monitor
- Real-time order tracking
- Position monitoring
- Market heatmaps
- Live charts

---

##  API Documentation

Once the backend is running, visit:

**Interactive API Docs**: http://localhost:8000/docs

### Key Endpoints

#### Authentication
- `POST /api/auth/signup` - Create new account
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Upstox Integration
- `GET /api/upstox/auth-url` - Get Upstox authorization URL
- `POST /api/upstox/callback` - Complete Upstox OAuth
- `GET /api/upstox/portfolio` - Fetch portfolio
- `GET /api/upstox/positions` - Get current positions
- `GET /api/upstox/market-quote/{symbol}` - Get live quote

#### Trading
- `GET /api/trading/dashboard` - Dashboard statistics
- `GET /api/trading/market-indices` - Market indices
- `POST /api/orders/` - Place new order
- `GET /api/orders/` - List all orders

#### AI Features
- `POST /api/ai/prompt` - Process AI trading prompt
- `GET /api/ai/market-analysis` - Get market analysis

#### Algorithm Management
- `GET /api/algorithms/` - List algorithms
- `POST /api/algorithms/` - Create new algorithm
- `PUT /api/algorithms/{id}` - Update algorithm
- `DELETE /api/algorithms/{id}` - Delete algorithm

---

##  Configuration

### Getting API Credentials

#### Upstox API
1. Visit [Upstox Developer Portal](https://upstox.com/developer/)
2. Create a new app
3. Get API Key and API Secret
4. Set redirect URI to `http://localhost:5173/callback`
5. Add credentials to `backend/.env`

#### Google Gemini AI
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `backend/.env` as `GEMINI_API_KEY`

### Environment Variables

Create `backend/.env`:
```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./quantai.db

# Security
SECRET_KEY=generate-a-secure-random-key-here

# Upstox
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_API_SECRET=your_upstox_api_secret
UPSTOX_REDIRECT_URI=http://localhost:5173/callback

# AI
GEMINI_API_KEY=your_gemini_api_key

# Trading
MAX_CAPITAL_PER_TRADE=100000
MAX_RISK_PERCENTAGE=2.0
```

---

##  Usage Guide

### 1. Create Account
1. Open http://localhost:5173
2. Click "Sign Up"
3. Enter your details
4. Login with your credentials

### 2. Connect Upstox
1. Go to Settings page
2. Click "Connect Upstox"
3. Authorize on Upstox website
4. You'll be redirected back

### 3. Use AI Trading Assistant
1. Go to AI Prompt page
2. Enter query like: "Find trending stocks in NIFTY 50"
3. Review AI suggestions
4. Execute trades

### 4. Create Trading Algorithm
1. Go to Algorithm Builder
2. Define strategy parameters
3. Save and activate
4. Monitor performance

### 5. Manage Risk
1. Go to Risk Manager
2. Set capital limits
3. Configure risk per trade
4. Monitor usage

---

##  Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` to secure random string
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS
- [ ] Configure CORS for production domain
- [ ] Set up proper logging
- [ ] Add rate limiting
- [ ] Enable monitoring
- [ ] Use environment-specific configs
- [ ] Set up CI/CD
- [ ] Configure backup strategy

### Recommended Stack
- **Frontend**: Vercel / Netlify
- **Backend**: AWS EC2 / DigitalOcean / Heroku
- **Database**: AWS RDS PostgreSQL
- **Monitoring**: Sentry / DataDog

---

##  Tech Stack

### Frontend
- React 18
- TypeScript 5
- Vite
- TailwindCSS
- Lucide React (icons)
- Recharts (charts)

### Backend
- FastAPI 0.109
- SQLAlchemy 2.0 (async)
- Pydantic 2.6
- JWT (python-jose)
- Bcrypt (passlib)
- Google Generative AI
- Upstox Python SDK

---

##  Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is free

### Frontend won't start
- Check Node version: `node --version` (need 16+)
- Install dependencies: `npm install`
- Check port 5173 is free

### Upstox connection fails
- Verify API credentials in `.env`
- Check redirect URI matches exactly
- Ensure app is approved by Upstox

### AI not working
- Add Gemini API key to `.env`
- Check API quota limits
- Verify internet connection

---

##  License

[MIT License](LICENSE)

---

##  Support

For issues, questions, or contributions:
- Backend API Docs: http://localhost:8000/docs
- Upstox API Docs: https://upstox.com/developer/api-documentation
- FastAPI Docs: https://fastapi.tiangolo.com/
- React Docs: https://react.dev/

---

##  Roadmap

- [ ] Websocket support for real-time updates
- [ ] Advanced charting with TradingView
- [ ] Backtest ing engine
- [ ] Paper trading mode
- [ ] Mobile app (React Native)
- [ ] Multi-broker support
- [ ] Social trading features
- [ ] Advanced analytics dashboard

---

**Built with  for Indian traders**

---

** Disclaimer**: This software is for educational purposes. Trading involves risk. Always do your own research and trade responsibly.
