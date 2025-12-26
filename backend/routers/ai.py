from fastapi import APIRouter, Depends, HTTPException
import google.generativeai as genai
import requests
import json
from models import User
from schemas import AIPromptRequest, AIPromptResponse, AICommandRequest, AICommandResponse
from utils.auth import get_current_user, get_optional_user
from config import settings
from sqlalchemy import desc, create_engine
from sqlalchemy.orm import sessionmaker, Session

# Create a synchronous engine for fallback price queries
_sync_engine = create_engine(settings.SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=_sync_engine)

router = APIRouter()


if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Using gemini-2.0-flash (gemini-1.5-flash has been deprecated)
    model = genai.GenerativeModel("gemini-2.0-flash")


def get_db_price(symbol: str) -> float:
    """Fetch latest closing price from database (Nifty100Daily or StockData)"""
    try:
        from models_ml import Nifty100Daily
        db = SessionLocal()
        try:
            latest = db.query(Nifty100Daily).filter(
                Nifty100Daily.symbol == symbol
            ).order_by(desc(Nifty100Daily.timestamp)).first()
            
            if latest:
                print(f"📊 DB price for {symbol}: {latest.close} (date: {latest.timestamp.date()})")
                return float(latest.close)
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ DB price error for {symbol}: {e}")
    
    # Try StockData table as fallback
    try:
        from models_alpha import StockData
        db = SessionLocal()
        try:
            latest = db.query(StockData).filter(
                StockData.symbol == symbol
            ).order_by(desc(StockData.timestamp)).first()
            
            if latest:
                print(f"📊 StockData price for {symbol}: {latest.close}")
                return float(latest.close)
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ StockData price error for {symbol}: {e}")
    
    return None


def get_best_price(symbol: str, access_token: str = None) -> float:
    """Get price from best available source: Upstox -> yFinance -> Database"""
    # Try Upstox first
    price = get_real_time_price(symbol, access_token)
    if price and price > 0:
        return price
    
    # Try Yahoo Finance
    price = get_yfinance_price(symbol)
    if price and price > 0:
        return price
    
    # Fallback to database
    price = get_db_price(symbol)
    if price and price > 0:
        return price
    
    return None


def _get_fallback_stocks_with_real_prices(stocks_template: list, access_token: str = None) -> list:
    """Update fallback stocks template with real prices from best available source"""
    updated_stocks = []
    for stock in stocks_template:
        stock_copy = stock.copy()
        price = get_best_price(stock["symbol"], access_token)
        if price and price > 0:
            stock_copy["current_price"] = round(price, 2)
            # Calculate entry/target/stop_loss based on real price
            if stock.get("trend") == "BULLISH" or stock.get("action") == "BUY":
                stock_copy["entry_price"] = round(price * 0.99, 2)  # 1% below
                stock_copy["target_price"] = round(price * 1.05, 2)  # 5% target
                stock_copy["stop_loss"] = round(price * 0.97, 2)  # 3% stop loss
            else:
                stock_copy["entry_price"] = round(price * 1.01, 2)  # 1% above for sell
                stock_copy["target_price"] = round(price * 0.95, 2)  # 5% target
                stock_copy["stop_loss"] = round(price * 1.03, 2)  # 3% stop loss
            # Also update breakout_level if present
            if "breakout_level" in stock_copy:
                stock_copy["breakout_level"] = round(price * 0.98, 2)
        updated_stocks.append(stock_copy)
    return updated_stocks

def get_real_time_price(symbol: str, access_token: str = None) -> float:
    """Fetch real-time price from Upstox API"""
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    if not access_token:
        return None
    
    # Map common symbols to Upstox instrument keys (NSE_EQ format)
    instrument_key = f"NSE_EQ|INE{symbol}"  # Basic format, may need mapping
    
    # Comprehensive Nifty 200 symbol to instrument key mapping
    symbol_mapping = {
        # Nifty 50 Stocks
        "RELIANCE": "NSE_EQ|INE002A01018",
        "TCS": "NSE_EQ|INE467B01029",
        "HDFCBANK": "NSE_EQ|INE040A01034",
        "INFY": "NSE_EQ|INE009A01021",
        "ICICIBANK": "NSE_EQ|INE090A01021",
        "LT": "NSE_EQ|INE018A01030",
        "SBIN": "NSE_EQ|INE062A01020",
        "BHARTIARTL": "NSE_EQ|INE397D01024",
        "HINDUNILVR": "NSE_EQ|INE030A01027",
        "ITC": "NSE_EQ|INE154A01025",
        "BAJFINANCE": "NSE_EQ|INE296A01024",
        "KOTAKBANK": "NSE_EQ|INE237A01028",
        "AXISBANK": "NSE_EQ|INE238A01034",
        "ASIANPAINT": "NSE_EQ|INE021A01026",
        "MARUTI": "NSE_EQ|INE585B01010",
        "TITAN": "NSE_EQ|INE280A01028",
        "SUNPHARMA": "NSE_EQ|INE044A01036",
        "NESTLEIND": "NSE_EQ|INE239A01016",
        "WIPRO": "NSE_EQ|INE075A01022",
        "ULTRACEMCO": "NSE_EQ|INE481G01011",
        "TATAMOTORS": "NSE_EQ|INE155A01022",
        "HCLTECH": "NSE_EQ|INE860A01027",
        "ONGC": "NSE_EQ|INE213A01029",
        "ADANIENT": "NSE_EQ|INE423A01024",
        "NTPC": "NSE_EQ|INE733E01010",
        "POWERGRID": "NSE_EQ|INE752E01010",
        "M&M": "NSE_EQ|INE101A01026",
        "JSWSTEEL": "NSE_EQ|INE019A01038",
        "TATASTEEL": "NSE_EQ|INE081A01020",
        "ADANIPORTS": "NSE_EQ|INE742F01042",
        "COALINDIA": "NSE_EQ|INE522F01014",
        "BAJAJFINSV": "NSE_EQ|INE918I01018",
        "HINDALCO": "NSE_EQ|INE038A01020",
        "TECHM": "NSE_EQ|INE669C01036",
        "DIVISLAB": "NSE_EQ|INE361B01024",
        "INDUSINDBK": "NSE_EQ|INE095A01012",
        "GRASIM": "NSE_EQ|INE047A01021",
        "CIPLA": "NSE_EQ|INE059A01026",
        "EICHERMOT": "NSE_EQ|INE066A01021",
        "DRREDDY": "NSE_EQ|INE089A01023",
        "HEROMOTOCO": "NSE_EQ|INE158A01026",
        "APOLLOHOSP": "NSE_EQ|INE437A01024",
        "TATACONSUM": "NSE_EQ|INE192A01025",
        "BRITANNIA": "NSE_EQ|INE216A01030",
        "SHRIRAMFIN": "NSE_EQ|INE721A01013",
        "SBILIFE": "NSE_EQ|INE123W01016",
        "BPCL": "NSE_EQ|INE029A01011",
        "LTIM": "NSE_EQ|INE214T01019",
        "ADANIGREEN": "NSE_EQ|INE364U01010",
        "PIDILITIND": "NSE_EQ|INE318A01026",
        
        # Additional Nifty Next 50 & Nifty 200 Stocks
        "HDFCLIFE": "NSE_EQ|INE795G01014",
        "DMART": "NSE_EQ|INE192R01011",
        "HAVELLS": "NSE_EQ|INE176B01034",
        "GODREJCP": "NSE_EQ|INE102D01028",
        "DABUR": "NSE_EQ|INE016A01026",
        "TORNTPHARM": "NSE_EQ|INE685A01028",
        "SIEMENS": "NSE_EQ|INE003A01024",
        "MOTHERSON": "NSE_EQ|INE775A01035",
        "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
        "AMBUJACEM": "NSE_EQ|INE079A01024",
        "DLF": "NSE_EQ|INE271C01023",
        "VEDL": "NSE_EQ|INE205A01025",
        "ICICIGI": "NSE_EQ|INE765G01017",
        "TVSMOTOR": "NSE_EQ|INE494B01023",
        "BOSCHLTD": "NSE_EQ|INE323A01026",
        "BERGEPAINT": "NSE_EQ|INE463A01038",
        "MARICO": "NSE_EQ|INE196A01026",
        "TRENT": "NSE_EQ|INE849A01020",
        "INDIGO": "NSE_EQ|INE646L01027",
        "ZOMATO": "NSE_EQ|INE758T01015",
        "COLPAL": "NSE_EQ|INE259A01022",
        "SAIL": "NSE_EQ|INE114A01011",
        "BEL": "NSE_EQ|INE263A01024",
        "JINDALSTEL": "NSE_EQ|INE749A01030",
        "GAIL": "NSE_EQ|INE129A01019",
        "CHOLAFIN": "NSE_EQ|INE121A01024",
        "HAL": "NSE_EQ|INE066F01012",
        "BANKBARODA": "NSE_EQ|INE028A01039",
        "ABB": "NSE_EQ|INE117A01022",
        "CANBK": "NSE_EQ|INE476A01022",
        "PNB": "NSE_EQ|INE160A01022",
        "UNIONBANK": "NSE_EQ|INE692A01016",
        "IDFCFIRSTB": "NSE_EQ|INE092T01019",
        "ALKEM": "NSE_EQ|INE540L01014",
        "LUPIN": "NSE_EQ|INE326A01037",
        "BIOCON": "NSE_EQ|INE376G01013",
        "AUROPHARMA": "NSE_EQ|INE406A01037",
        "PAGEIND": "NSE_EQ|INE761H01022",
        "MCDOWELL-N": "NSE_EQ|INE254A01020",
        "BAJAJHLDNG": "NSE_EQ|INE118A01012",
        "IGL": "NSE_EQ|INE203G01027",
        "MUTHOOTFIN": "NSE_EQ|INE414G01012",
        "LICHSGFIN": "NSE_EQ|INE013A01015",
        "PFC": "NSE_EQ|INE134E01011",
        "RECLTD": "NSE_EQ|INE020B01018",
        "OFSS": "NSE_EQ|INE881D01027",
        "PERSISTENT": "NSE_EQ|INE262H01013",
        "COFORGE": "NSE_EQ|INE591G01017",
        "MPHASIS": "NSE_EQ|INE356A01018",
        "LAURUSLABS": "NSE_EQ|INE947Q01028",
        "TORNTPOWER": "NSE_EQ|INE813H01021",
        "PIIND": "NSE_EQ|INE603J01030",
        "VOLTAS": "NSE_EQ|INE226A01021",
        "GODREJPROP": "NSE_EQ|INE484J01027",
        "OBEROIRLTY": "NSE_EQ|INE093I01010",
        "PRESTIGE": "NSE_EQ|INE811K01011",
        "BRIGADE": "NSE_EQ|INE791I01019",
        "SBICARD": "NSE_EQ|INE018E01016",
        "AUBANK": "NSE_EQ|INE949L01017",
        "BANDHANBNK": "NSE_EQ|INE545U01014",
        "FEDERALBNK": "NSE_EQ|INE171A01029",
        "IDFCBANK": "NSE_EQ|INE092T01019",
        "INDUSTOWER": "NSE_EQ|INE121J01017",
        "TATACOMM": "NSE_EQ|INE151A01013",
        "ZEEL": "NSE_EQ|INE256A01028",
        "PVR": "NSE_EQ|INE191H01014",
        "DIXON": "NSE_EQ|INE935N01012",
        "POLICYBZR": "NSE_EQ|INE417T01026",
        "PAYTM": "NSE_EQ|INE982J01020",
        "NYKAA": "NSE_EQ|INE388Y01029",
        "JINDAL": "NSE_EQ|INE749A01030",
        "ACC": "NSE_EQ|INE012A01025",
        "AMBUJAC": "NSE_EQ|INE079A01024",
        "SHREECEM": "NSE_EQ|INE070A01015",
        "RAMCOCEM": "NSE_EQ|INE331A01037",
        "CUMMINSIND": "NSE_EQ|INE298A01020",
        "THERMAX": "NSE_EQ|INE152A01029",
        "HONAUT": "NSE_EQ|INE671A01010",
        "SCHAEFFLER": "NSE_EQ|INE513A01022",
        "SKFINDIA": "NSE_EQ|INE640A01023",
        "APLAPOLLO": "NSE_EQ|INE702C01027",
        "ASTRAL": "NSE_EQ|INE006I01046",
        "RELAXO": "NSE_EQ|INE131B01039",
        "VBL": "NSE_EQ|INE200M01021",
        "TATAELXSI": "NSE_EQ|INE670A01012",
        "COROMANDEL": "NSE_EQ|INE169A01031",
        "DEEPAKNI": "NSE_EQ|INE288B01029",
        "GNFC": "NSE_EQ|INE113A01013",
        "AARTI": "NSE_EQ|INE769A01020",
        "SRF": "NSE_EQ|INE647A01010",
        "BALKRISIND": "NSE_EQ|INE787D01026",
        "APOLLOTYRE": "NSE_EQ|INE438A01022",
        "MRF": "NSE_EQ|INE883A01011",
        "CEAT": "NSE_EQ|INE482A01020",
        "JKCEMENT": "NSE_EQ|INE823G01014",
        "CROMPTON": "NSE_EQ|INE299U01018",
        "VGUARD": "NSE_EQ|INE951I01027",
        "WHIRLPOOL": "NSE_EQ|INE716A01013",
        "BLUESTAR": "NSE_EQ|INE472A01039",
        "CLEAN": "NSE_EQ|INE145O01016",
        "GRINDWELL": "NSE_EQ|INE536A01023",
        "CARBORUNIV": "NSE_EQ|INE120A01034",
        "SUMICHEM": "NSE_EQ|INE258A01016",
        "NAVINFLUOR": "NSE_EQ|INE048G01026",
        "FLUOROCHEM": "NSE_EQ|INE09N01012",
        "MINDACORP": "NSE_EQ|INE842C01021",
        "INDHOTEL": "NSE_EQ|INE053A01029",
        "LEMONTREE": "NSE_EQ|INE970X01018",
        "MAHLOG": "NSE_EQ|INE766P01016",
        "BLUEDART": "NSE_EQ|INE233B01017",
        "VTL": "NSE_EQ|INE825A01012",
        "CONCOR": "NSE_EQ|INE111A01025",
        "APOLLOTYRE": "NSE_EQ|INE438A01022",
        "EXIDEIND": "NSE_EQ|INE302A01020",
        "AMARAJABAT": "NSE_EQ|INE885A01032",
        "ASHOKLEY": "NSE_EQ|INE208A01029",
        "ESCORTS": "NSE_EQ|INE042A01014",
        "SWARAJENG": "NSE_EQ|INE277A01016",
        "SONACOMS": "NSE_EQ|INE529A01010",
        "BHARATFORG": "NSE_EQ|INE465A01025",
        "ENDURANCE": "NSE_EQ|INE913H01037",
        "BOMDYEING": "NSE_EQ|INE032A01023",
        "CENTURYTEX": "NSE_EQ|INE055A01016",
        "GUJGASLTD": "NSE_EQ|INE844O01030",
        "MGL": "NSE_EQ|INE002S01010",
        "PETRONET": "NSE_EQ|INE347G01014",
        "ATGL": "NSE_EQ|INE824G01012",
        "GSPL": "NSE_EQ|INE246F01010",
        "IOC": "NSE_EQ|INE242A01010",
        "HINDPETRO": "NSE_EQ|INE094A01015",
        "MGL": "NSE_EQ|INE002S01010",
        "JUBLFOOD": "NSE_EQ|INE797F01020",
        "WESTLIFE": "NSE_EQ|INE274F01020",
        "DEVYANI": "NSE_EQ|INE872J01023",
        "VAIBHAVGBL": "NSE_EQ|INE884A01027",
        "SHOPERSTOP": "NSE_EQ|INE498B01024",
        "ADITYA": "NSE_EQ|INE750A01020",
        "RAYMONDS": "NSE_EQ|INE301A01014",
        "BATAINDIA": "NSE_EQ|INE176A01028",
        "RELAXO": "NSE_EQ|INE131B01039",
    }
    
    instrument_key = symbol_mapping.get(symbol, f"NSE_EQ|{symbol}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(
            f"https://api.upstox.com/v2/market-quote/ltp?symbol={instrument_key}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # Extract LTP from response
            if data.get("status") == "success" and data.get("data"):
                # Upstox might return a different key than requested (e.g. NSE_EQ:RELIANCE vs NSE_EQ|INE...)
                # Since we request one symbol, we can just take the first item.
                if data['data']:
                    ltp_data = next(iter(data['data'].values()))
                    return ltp_data.get("last_price")
        return None
    except Exception as e:
        print(f"Error fetching price for {symbol}: {str(e)}")
        return None

def get_yfinance_price(symbol: str) -> float:
    """Fetch price from Yahoo Finance as fallback"""
    try:
        import yfinance as yf
        # Append .NS for NSE stocks
        ticker = f"{symbol}.NS"
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        return float(price)
    except Exception as e:
        print(f"Error fetching YFinance price for {symbol}: {e}")
        return None


@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(request: AIPromptRequest, current_user: User = Depends(get_optional_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        enhanced_prompt = f"""You are a professional stock trading advisor for the Indian stock market (NSE Cash Segment only).

User Query: {request.prompt}

IMPORTANT: Respond ONLY with a valid JSON array of stock recommendations. Do not include any other text, markdown formatting, or code blocks.

Each stock recommendation must follow this exact structure:
[
  {{
    "symbol": "STOCK_SYMBOL",
    "name": "Company Full Name",
    "action": "BUY" or "SELL" or "WAIT",
    "trade_type": "Intraday" or "Short-Term" or "Weekly",
    "price": current_price_estimate,
    "entry_price": recommended_entry_price,
    "target_price": target_price_for_profit,
    "stop_loss": stop_loss_price,
    "risk_reward": "1:2" or "1:3" etc,
    "confidence": confidence_percentage (0-100),
    "reason": "Brief explanation of why this stock is recommended (max 200 characters)"
  }}
]

Guidelines:
- Provide 3-5 specific stock recommendations from NIFTY 50/200
- Use actual NSE stock symbols (e.g., "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK")
- Base recommendations on current market trends, technical analysis, and sector performance
- entry_price should be slightly below current price for BUY (or above for SELL)
- target_price should reflect realistic profit target based on trend analysis
- stop_loss should be set at a logical support/resistance level
- risk_reward should be at least 1:1.5 or better
- Confidence should reflect how strong the signal is (80%+ for strong signals, 50-79% for moderate, below 50% for weak)
- Keep reasons concise and actionable
- Only respond with the JSON array, nothing else"""
        
        print(f"Processing AI prompt: {request.prompt}")
        response = model.generate_content(enhanced_prompt)
        response_text = response.text.strip()
        print(f"Got AI response, length: {len(response_text)}")
        
        suggested_stocks = []
        fallback_used = False
        
        # Clean up the response to extract JSON
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            # Attempt to parse the AI response as JSON
            parsed_response = json.loads(response_text)
            
            # Validate the structure of each recommendation and fetch LTP
            if isinstance(parsed_response, list):
                for stock_rec in parsed_response:
                    # Check for core required fields only
                    if not all(k in stock_rec for k in ["symbol", "action", "confidence", "reason"]):
                        print(f"Invalid stock recommendation structure from AI: {stock_rec}")
                        fallback_used = True
                        break # Break out of the loop if any recommendation is invalid
                    
                    # Fetch current price for the recommended stock
                    access_token = (current_user.upstox_access_token if current_user and getattr(current_user, "upstox_access_token", None) else None) or settings.UPSTOX_ACCESS_TOKEN
                    
                    current_price = None
                    if access_token:
                        current_price = get_real_time_price(stock_rec["symbol"], access_token)
                    
                    # Fallback to Yahoo Finance if Upstox fails
                    if current_price is None or current_price == 0:
                        print(f"Upstox price failed for {stock_rec['symbol']}, trying Yahoo Finance...")
                        current_price = get_yfinance_price(stock_rec["symbol"])

                    if current_price is not None and current_price > 0:
                        stock_rec["price"] = current_price
                        
                        # Calculate trade levels if not provided by AI
                        if not stock_rec.get("entry_price") or stock_rec.get("entry_price") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["entry_price"] = round(current_price * 0.995, 2)  # 0.5% below current
                            else:
                                stock_rec["entry_price"] = round(current_price * 1.005, 2)  # 0.5% above current
                        
                        if not stock_rec.get("target_price") or stock_rec.get("target_price") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["target_price"] = round(current_price * 1.03, 2)  # +3% target
                            else:
                                stock_rec["target_price"] = round(current_price * 0.97, 2)  # -3% target
                        
                        if not stock_rec.get("stop_loss") or stock_rec.get("stop_loss") == 0:
                            if stock_rec["action"] == "BUY":
                                stock_rec["stop_loss"] = round(current_price * 0.985, 2)  # -1.5% stop loss
                            else:
                                stock_rec["stop_loss"] = round(current_price * 1.015, 2)  # +1.5% stop loss
                        
                        if not stock_rec.get("risk_reward"):
                            stock_rec["risk_reward"] = "1:2"
                        
                        if not stock_rec.get("trade_type"):
                            stock_rec["trade_type"] = "Short-Term"
                    else:
                        print(f"Could not fetch price for {stock_rec['symbol']} from any source. Setting to 0.")
                        stock_rec["price"] = stock_rec.get("price", 0)
                    
                    suggested_stocks.append(stock_rec)
            else:
                print("AI response was not a JSON list. Using fallback.")
                fallback_used = True

        except json.JSONDecodeError:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"JSON Decode Error. Response text: {response_text}\n")
            print("AI response was not valid JSON. Using fallback.")
            fallback_used = True
        except ValueError as ve:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"Value Error: {ve}\n")
            print(f"AI response structure invalid: {ve}. Using fallback.")
            fallback_used = True
        except Exception as e:
            with open("debug_ai_error.log", "a") as f:
                f.write(f"General Error: {e}\n")
            print(f"Error processing AI response or fetching LTP: {e}. Using fallback.")
            fallback_used = True

        if fallback_used or not suggested_stocks:
            suggested_stocks = [
                {
                    "symbol": "RELIANCE",
                    "name": "Reliance Industries Ltd",
                    "action": "BUY",
                    "trade_type": "Short-Term",
                    "price": 1556.50,
                    "entry_price": 1550.00,
                    "target_price": 1610.00,
                    "stop_loss": 1520.00,
                    "risk_reward": "1:2",
                    "confidence": 75,
                    "reason": "AI response parsing failed. This is sample data. Please try again with a different query."
                }
            ]
        
        return {
            "response": response_text,
            "suggested_stocks": suggested_stocks,
            "strategy": {"type": "ai_generated", "confidence": "high"}
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

@router.get("/market-analysis")
async def get_market_analysis(current_user: User = Depends(get_optional_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        prompt = """Provide a brief daily market analysis for the Indian stock market (NIFTY 50).
Include: 1. Market sentiment 2. Key sectors 3. Support/resistance levels 4. Trading recommendation"""
        
        response = model.generate_content(prompt)
        return {"analysis": response.text, "market_sentiment": "Bullish"}
    except Exception as e:
        print(f"AI Market Analysis failed: {e}")
        # Fallback to a static or semi-dynamic analysis if AI fails
        return {
            "analysis": "The market is showing consolidation with a slight bullish bias. Key resistance at 24,500 and support at 24,000 for NIFTY 50. Sectors to watch: IT, Banking and Auto. (Fallback analysis due to AI service busy)",
            "market_sentiment": "Stable",
            "fallback": True
        }

@router.get("/trend-finder")
async def get_trend_finder_stocks(current_user: User = Depends(get_optional_user)):
    """
    Identify stocks with strong trend continuation setups using technical analysis.
    
    Uses quantitative indicators:
    - 20-EMA Trend Filter (25%)
    - RSI Momentum 40-70 zone (20%)
    - Volume Confirmation >1.5x (15%)
    - Pullback Detection (25%)
    - ADX Strength >25 (15%)
    
    Returns stocks with score >= 60, enriched with LIVE prices from Upstox.
    """
    try:
        from services.trend_analyzer import TrendAnalyzer
        from services.live_price_enricher import enrich_scanner_results
        
        analyzer = TrendAnalyzer()
        stocks = analyzer.scan_all(limit=10)
        
        if stocks:
            # Enrich with live prices from Upstox
            access_token = settings.UPSTOX_ACCESS_TOKEN
            enriched_stocks = enrich_scanner_results(stocks, access_token)
            
            return {
                "status": "success",
                "count": len(enriched_stocks),
                "stocks": enriched_stocks,
                "scan_type": "trend_technical",
                "description": "Stocks identified using technical analysis with LIVE prices (EMA, RSI, ADX, Volume, Pullback)"
            }
        else:
            # No stocks met criteria - return message
            return {
                "status": "success",
                "count": 0,
                "stocks": [],
                "scan_type": "trend_technical",
                "description": "No stocks currently meet the trend criteria (score >= 60). Market may be in consolidation."
            }
            
    except Exception as e:
        print(f"Trend finder error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Fallback to database price lookup for sample stocks
        fallback_template = [
            {"symbol": "RELIANCE", "name": "Reliance Industries", "trend": "BULLISH", "strength": 70, "current_price": 0, "entry_price": 0, "target_price": 0, "stop_loss": 0, "reason": "Technical analysis service error - showing sample data"},
            {"symbol": "TCS", "name": "Tata Consultancy Services", "trend": "BULLISH", "strength": 65, "current_price": 0, "entry_price": 0, "target_price": 0, "stop_loss": 0, "reason": "Technical analysis service error - showing sample data"},
            {"symbol": "HDFCBANK", "name": "HDFC Bank", "trend": "BULLISH", "strength": 60, "current_price": 0, "entry_price": 0, "target_price": 0, "stop_loss": 0, "reason": "Technical analysis service error - showing sample data"}
        ]
        access_token = settings.UPSTOX_ACCESS_TOKEN
        fallback_stocks = _get_fallback_stocks_with_real_prices(fallback_template, access_token)
        return {
            "status": "success",
            "count": len(fallback_stocks),
            "stocks": fallback_stocks,
            "scan_type": "trend_fallback",
            "description": "Technical analysis service error - showing sample data with real prices"
        }

@router.get("/breakout-detector")
async def get_breakout_stocks(current_user: User = Depends(get_optional_user)):
    """
    Detect stocks with volume-backed breakouts using technical analysis.
    
    Breakout Types:
    - 52W_HIGH: New 52-week high with volume
    - RESISTANCE: Breaking 20-day high resistance
    - CONSOLIDATION: ATR expansion after low volatility
    """
    try:
        from services.breakout_detector import BreakoutDetector
        from services.live_price_enricher import enrich_scanner_results
        
        detector = BreakoutDetector()
        stocks = detector.scan_all(limit=10)
        
        if stocks:
            # Enrich with live prices from Upstox
            access_token = settings.UPSTOX_ACCESS_TOKEN
            enriched_stocks = enrich_scanner_results(stocks, access_token)
            
            return {
                "status": "success",
                "count": len(enriched_stocks),
                "stocks": enriched_stocks,
                "scan_type": "breakout_technical",
                "description": "Breakout stocks with LIVE prices (52W High, Resistance, Volume)"
            }
        else:
            return {
                "status": "success",
                "count": 0,
                "stocks": [],
                "scan_type": "breakout_technical",
                "description": "No breakout stocks currently meet the criteria (score >= 60)"
            }
            
    except Exception as e:
        print(f"Breakout detector error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        fallback_template = [
            {"symbol": "TATAMOTORS", "name": "Tata Motors", "trend": "BULLISH", "breakout_type": "RESISTANCE", "volume_ratio": 1.5, "current_price": 0, "breakout_level": 0, "target_price": 0, "stop_loss": 0, "strength": 60, "reason": "Technical analysis service error"},
        ]
        access_token = settings.UPSTOX_ACCESS_TOKEN
        fallback_stocks = _get_fallback_stocks_with_real_prices(fallback_template, access_token)
        return {
            "status": "success",
            "count": len(fallback_stocks),
            "stocks": fallback_stocks,
            "scan_type": "breakout_fallback",
            "description": "Technical analysis service error - showing sample data"
        }

@router.get("/top5-picks")
async def get_top5_picks(current_user: User = Depends(get_optional_user)):
    """
    Get Top 10 Buy/Sell signals (5 BUY + 5 SELL) using technical analysis.
    
    Criteria:
    - EMA alignment (9/21 crossover)
    - RSI momentum (40-70 for BUY, inverse for SELL)
    - Volume confirmation
    - MACD histogram
    """
    try:
        from services.top5_buysell import Top5BuySellEngine
        from services.live_price_enricher import enrich_scanner_results
        
        engine = Top5BuySellEngine()
        signals = engine.scan_all(limit=5)
        
        # Enrich with live prices from Upstox
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_buy = enrich_scanner_results(signals.get("buy", []), access_token)
        enriched_sell = enrich_scanner_results(signals.get("sell", []), access_token)
        all_stocks = enriched_buy + enriched_sell
        
        return {
            "status": "success",
            "count": len(all_stocks),
            "stocks": all_stocks,
            "buy_signals": enriched_buy,
            "sell_signals": enriched_sell,
            "scan_type": "top10_technical",
            "description": "Top 10 Buy/Sell signals with LIVE prices (EMA, RSI, MACD, Volume)"
        }
            
    except Exception as e:
        print(f"Top 5 picks error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        fallback_template = [
            {"symbol": "RELIANCE", "name": "Reliance Industries", "action": "BUY", "confidence": 70, "current_price": 0, "entry_range": "", "target_1": 0, "target_2": 0, "stop_loss": 0, "expected_move": "+2%", "reason": "Technical analysis service error"},
        ]
        access_token = settings.UPSTOX_ACCESS_TOKEN
        fallback_stocks = _get_fallback_stocks_with_real_prices(fallback_template, access_token)
        return {
            "status": "success",
            "count": len(fallback_stocks),
            "stocks": fallback_stocks,
            "scan_type": "top5_fallback",
            "description": "Technical analysis service error - showing sample data"
        }

# Keep legacy endpoint for backwards compatibility
@router.get("/top3-picks")
async def get_top3_picks(current_user: User = Depends(get_optional_user)):
    """Legacy endpoint - redirects to top5-picks"""
    return await get_top5_picks(current_user)

@router.get("/momentum-scanner")
async def get_momentum_stocks(current_user: User = Depends(get_optional_user)):
    """Momentum Scanner - ROC and MFI based with LIVE prices."""
    try:
        from services.momentum_scanner import MomentumScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = MomentumScanner()
        stocks = scanner.scan_all(limit=10)
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "momentum", "description": "Stocks with strong price momentum (LIVE prices)"}
    except Exception as e:
        print(f"Momentum scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "momentum", "description": str(e)}

@router.get("/mean-reversion")
async def get_mean_reversion_stocks(current_user: User = Depends(get_optional_user)):
    """Mean Reversion Scanner with LIVE prices."""
    try:
        from services.mean_reversion_scanner import MeanReversionScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = MeanReversionScanner()
        stocks = scanner.scan_all(limit=10)
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "mean_reversion", "description": "Oversold/overbought stocks with LIVE prices"}
    except Exception as e:
        print(f"Mean reversion error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "mean_reversion", "description": str(e)}

@router.get("/gap-scanner")
async def get_gap_stocks(current_user: User = Depends(get_optional_user)):
    """Gap Scanner - Overnight gap detection."""
    try:
        from services.gap_scanner import GapScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = GapScanner()
        stocks = scanner.scan_all(limit=10)
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "gap", "description": "Gap stocks with LIVE prices"}
    except Exception as e:
        print(f"Gap scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "gap", "description": str(e)}

@router.get("/relative-strength")
async def get_relative_strength_stocks(current_user: User = Depends(get_optional_user)):
    """Relative Strength Scanner - Market outperformers."""
    try:
        from services.relative_strength_scanner import RelativeStrengthScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = RelativeStrengthScanner()
        stocks = scanner.scan_all(limit=10)
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "relative_strength", "description": "Market outperformers with LIVE prices"}
    except Exception as e:
        print(f"Relative strength error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "relative_strength", "description": str(e)}

@router.get("/vwap-scanner")
async def get_vwap_stocks(current_user: User = Depends(get_optional_user)):
    """VWAP Scanner - Volume weighted average price trading."""
    try:
        from services.vwap_scanner import VWAPScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = VWAPScanner()
        stocks = scanner.scan_all(limit=10)
        
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "vwap", "description": "VWAP trading signals with LIVE prices"}
    except Exception as e:
        print(f"VWAP scanner error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "vwap", "description": str(e)}

@router.get("/sr-bounce")
async def get_sr_bounce_stocks(current_user: User = Depends(get_optional_user)):
    """Support/Resistance Bounce Scanner with LIVE prices."""
    try:
        from services.sr_bounce_scanner import SRBounceScanner
        from services.live_price_enricher import enrich_scanner_results
        
        scanner = SRBounceScanner()
        stocks = scanner.scan_all(limit=10)
        
        # Enrich with live prices from Upstox
        access_token = settings.UPSTOX_ACCESS_TOKEN
        enriched_stocks = enrich_scanner_results(stocks, access_token)
        
        return {"status": "success", "count": len(enriched_stocks), "stocks": enriched_stocks,
                "scan_type": "sr_bounce", "description": "Stocks bouncing off support/resistance levels with LIVE prices"}
    except Exception as e:
        print(f"S/R bounce error: {e}")
        return {"status": "success", "count": 0, "stocks": [], "scan_type": "sr_bounce", "description": str(e)}

@router.post("/command", response_model=AICommandResponse)
async def process_command(request: AICommandRequest, current_user: User = Depends(get_current_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        prompt = f"""
        Convert the following natural language command into a JSON action object.
        User Command: "{request.command}"
        
        Supported Actions:
        - start_intraday_bot (params: capital, max_positions, strategy)
        - stop_bot
        - scan_market (params: index e.g. "Nifty 200")
        - backtest (params: strategy, period, capital)
        - update_risk_settings (params: max_loss, max_position_size)
        - fetch_trending_stocks
        
        Output JSON ONLY. Example: {{"action": "start_intraday_bot", "capital": 100000, "strategy": "trend"}}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        action_data = json.loads(response_text)
        action = action_data.get("action", "unknown")
        
        return {
            "action": action,
            "params": action_data,
            "message": f"Command parsed: {action}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command processing failed: {str(e)}")


@router.get("/sentiment")
async def get_ai_sentiment(
    symbol: str,
    current_user: User = Depends(get_optional_user)
):
    """
    Secure AI sentiment proxy endpoint.
    
    This keeps the Gemini API key server-side and prevents frontend exposure.
    The frontend should call this endpoint instead of directly using
    the Google AI SDK.
    
    Returns:
        JSON with sentiment (BULLISH/BEARISH/NEUTRAL), ltp, and summary
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    try:
        prompt = f"""
        Task: Analyze current market sentiment for {symbol} (Indian Stock Market, NSE).
        
        Based on recent market trends, news, and technical indicators:
        1. Determine the overall sentiment
        2. Provide a brief market outlook
        
        Respond ONLY with a valid JSON object:
        {{
            "sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
            "ltp": estimated_current_price_number,
            "summary": "Brief 1-2 sentence market outlook for this stock"
        }}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback parsing
            result = {
                "sentiment": "NEUTRAL",
                "ltp": None,
                "summary": "Unable to parse AI response. Please try again."
            }
        
        # Try to get real price if AI didn't provide one
        if not result.get("ltp"):
            price = get_best_price(symbol, settings.UPSTOX_ACCESS_TOKEN)
            if price:
                result["ltp"] = round(price, 2)
        
        return {
            "symbol": symbol,
            "sentiment": result.get("sentiment", "NEUTRAL"),
            "ltp": result.get("ltp"),
            "summary": result.get("summary", "Market data retrieved."),
            "source": "gemini-ai"
        }
        
    except Exception as e:
        print(f"AI sentiment error for {symbol}: {e}")
        
        # Fallback with real price
        price = get_best_price(symbol, settings.UPSTOX_ACCESS_TOKEN)
        
        return {
            "symbol": symbol,
            "sentiment": "NEUTRAL",
            "ltp": round(price, 2) if price else None,
            "summary": "AI service temporarily unavailable. Showing current market price.",
            "source": "fallback"
        }

