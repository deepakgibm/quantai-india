# QuantAI India - Complete Setup Guide

##  Full-Stack Trading Bot with Upstox Integration

This project includes a modern React frontend and FastAPI backend for AI-powered trading.

##  Project Structure

```
quantai-india/
 frontend (React + TypeScript + Vite)
    pages/          # All UI pages
    components/     # Reusable components
    services/       # API integration
    types.ts        # TypeScript types

 backend/ (FastAPI + SQLAlchemy)
     routers/        # API endpoints
     models.py       # Database models
     schemas.py      # Pydantic schemas
     utils/          # Helper functions
     config.py       # Configuration
     database.py     # Database setup
```

##  Backend Setup

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `backend/.env` and add your credentials:

```env
# Upstox API Credentials (Get from https://upstox.com/developer/)
UPSTOX_API_KEY=your_upstox_api_key_here
UPSTOX_API_SECRET=your_upstox_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:5173/callback

# Gemini AI API Key (Get from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# Security (Change in production!)
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
```

### 3. Start Backend Server

```bash
python main.py
```

Backend will run at: **http://localhost:8000**

API Documentation: **http://localhost:8000/docs**

##  Frontend Setup

### 1. Install Node Dependencies

```bash
cd ..  # Back to root directory
npm install
```

### 2. Configure Frontend

Edit `services/api.ts` and set:

```typescript
const USE_MOCK = false;  // Set to false to use real backend
```

### 3. Start Frontend Server

```bash
npm run dev
```

Frontend will run at: **http://localhost:5173**

##  Getting API Credentials

### Upstox API Setup

1. Visit [Upstox Developer Portal](https://upstox.com/developer/)
2. Create a new app
3. Get your **API Key** and **API Secret**
4. Set redirect URI to `http://localhost:5173/callback`
5. Add credentials to `backend/.env`

### Gemini AI Setup

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `backend/.env` as `GEMINI_API_KEY`

##  API Endpoints

### Authentication
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Upstox Integration
- `GET /api/upstox/auth-url` - Get Upstox auth URL
- `POST /api/upstox/callback` - Exchange code for token
- `GET /api/upstox/portfolio` - Get holdings
- `GET /api/upstox/positions` - Get positions
- `GET /api/upstox/market-quote/{symbol}` - Get live quotes

### Trading
- `GET /api/trading/dashboard` - Dashboard stats
- `GET /api/trading/market-indices` - Market indices
- `POST /api/orders/` - Place order
- `GET /api/orders/` - Get all orders

### AI Features
- `POST /api/ai/prompt` - Process AI trading prompt
- `GET /api/ai/market-analysis` - Get market analysis

### Algorithms
- `GET /api/algorithms/` - List algorithms
- `POST /api/algorithms/` - Create algorithm
- `PUT /api/algorithms/{id}` - Update algorithm

### Risk & Settings
- `GET /api/risk/` - Get risk settings
- `PUT /api/risk/` - Update risk settings
- `GET /api/settings/` - Get user settings
- `PUT /api/settings/` - Update settings

##  Usage Flow

### First Time Setup

1. **Start Backend**: `cd backend && python main.py`
2. **Start Frontend**: `npm run dev`
3. **Create Account**: Go to http://localhost:5173 and sign up
4. **Connect Upstox**:
   - Click "Connect Upstox" in Settings
   - Authorize on Upstox website
   - You'll be redirected back with access
5. **Start Trading**: Use AI prompts or manual trading

### Using the Trading Bot

1. **Dashboard**: View portfolio, P&L, and market overview
2. **AI Prompt**: Ask AI for trading suggestions
   - Example: "Find trending stocks in NIFTY 50"
   - Example: "What are the best breakout stocks today?"
3. **Algorithms**: Create and activate trading algorithms
4. **Orders**: Place and track orders
5. **Risk Management**: Set capital limits and risk parameters
6. **Live Monitor**: Watch real-time market data

##  Development

### Run Backend with Hot Reload

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend with Hot Reload

```bash
npm run dev
```

### Database Management

The backend uses SQLite. Database file: `backend/quantai.db`

To reset database:
```bash
cd backend
rm quantai.db
python main.py  # Will recreate database
```

##  Security Notes

- Change `SECRET_KEY` in production
- Never commit `.env` files
- Use HTTPS in production
- Implement rate limiting for production
- Rotate API keys regularly

##  Tech Stack

### Frontend
- **React** with TypeScript
- **Vite** for fast development
- **Lucide React** for icons
- **Recharts** for charts
- **TailwindCSS** for styling

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Async ORM
- **Pydantic** - Data validation
- **JWT** - Authentication
- **Upstox SDK** - Broker integration
- **Google Gemini** - AI capabilities

##  Troubleshooting

### Backend won't start
- Check Python version (3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check if port 8000 is available

### Frontend won't start
- Check Node version (16+)
- Install dependencies: `npm install`
- Check if port 5173 is available

### Upstox connection fails
- Verify API credentials in `.env`
- Check redirect URI matches exactly
- Ensure Upstox app is approved

### AI not working
- Add Gemini API key to `.env`
- Check API quota limits
- Verify network connection

##  Support

For issues:
- Backend API Docs: http://localhost:8000/docs
- Upstox Docs: https://upstox.com/developer/api-documentation
- FastAPI Docs: https://fastapi.tiangolo.com/

##  Production Deployment

1. Set environment variables properly
2. Use production database (PostgreSQL recommended)
3. Enable HTTPS
4. Set up CORS properly
5. Add rate limiting
6. Use environment-specific configs
7. Monitor with logging/metrics

---

**Happy Trading! **
