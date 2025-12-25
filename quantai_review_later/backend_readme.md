# QuantAI India - Backend API

## FastAPI Backend with Upstox Integration

This is the backend API for the QuantAI India Trading Bot with full Upstox broker integration.

## Features

- **User Authentication** - JWT-based signup/login
- **Upstox Integration** - OAuth2 flow, portfolio, positions, market data
- **AI-Powered Trading** - Gemini AI for market analysis and trade suggestions
- **Order Management** - Place, track, and manage orders
- **Risk Management** - Capital allocation and risk controls
- **Algorithm Management** - Create and manage trading algorithms
- **Real-time Market Data** - Live quotes and indices

## Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment Variables**

Edit `.env` file and add your credentials:
- `UPSTOX_API_KEY` - Your Upstox API Key
- `UPSTOX_API_SECRET` - Your Upstox API Secret
- `GEMINI_API_KEY` - Your Google Gemini API Key

3. **Run the Server**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Upstox Integration

### Getting Upstox API Credentials

1. Visit [Upstox Developer Portal](https://upstox.com/developer/)
2. Create an app and get API Key & Secret
3. Set redirect URI to `http://localhost:5173/callback`

### Authentication Flow

1. User clicks "Connect Upstox" in frontend
2. Backend provides auth URL (`/api/upstox/auth-url`)
3. User authorizes on Upstox
4. Upstox redirects to frontend with code
5. Frontend sends code to backend (`/api/upstox/callback`)
6. Backend exchanges code for access token
7. Token saved to user account

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Upstox
- `GET /api/upstox/auth-url` - Get Upstox authorization URL
- `POST /api/upstox/callback` - Handle Upstox callback
- `GET /api/upstox/portfolio` - Get user portfolio
- `GET /api/upstox/positions` - Get current positions
- `GET /api/upstox/market-quote/{symbol}` - Get market quote

### Trading
- `GET /api/trading/dashboard` - Get dashboard statistics
- `GET /api/trading/market-indices` - Get market indices
- `GET /api/trading/top-gainers` - Get top gaining stocks

### Orders
- `POST /api/orders/` - Place new order
- `GET /api/orders/` - Get all orders
- `GET /api/orders/{id}` - Get specific order

### AI
- `POST /api/ai/prompt` - Process AI trading prompt
- `GET /api/ai/market-analysis` - Get AI market analysis

### Algorithms
- `POST /api/algorithms/` - Create algorithm
- `GET /api/algorithms/` - Get all algorithms
- `GET /api/algorithms/{id}` - Get specific algorithm
- `PUT /api/algorithms/{id}` - Update algorithm
- `DELETE /api/algorithms/{id}` - Delete algorithm

### Risk Management
- `GET /api/risk/` - Get risk settings
- `PUT /api/risk/` - Update risk settings

### Settings
- `GET /api/settings/` - Get user settings
- `PUT /api/settings/` - Update user settings

## Database

Uses SQLite with async support (aiosqlite). Database file: `quantai.db`

Tables:
- `users` - User accounts
- `orders` - Trading orders
- `algorithms` - Trading algorithms
- `user_settings` - User preferences

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM with async support
- **Pydantic** - Data validation
- **JWT** - Authentication tokens
- **Upstox API** - Broker integration
- **Google Gemini** - AI capabilities

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Security Notes

- Change `SECRET_KEY` in production
- Never commit `.env` file
- Use HTTPS in production
- Implement rate limiting
- Add input validation

## Support

For issues or questions, please refer to:
- [Upstox API Docs](https://upstox.com/developer/api-documentation)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
