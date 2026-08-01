"""
QuantAI India SaaS API Router
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from utils.auth import get_current_user
from database import get_db

# Service imports
from services.saas.subscription_service import SubscriptionService
from services.saas.smc_service import SMCService
from services.saas.pattern_recognition_service import PatternRecognitionService
from services.saas.academy_service import AcademyService

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── SUBSCRIPTION ROUTES ──────────────────────────────────────────────────────

@router.get("/subscription")
async def get_subscription_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        sub = await SubscriptionService.get_active_subscription(db, current_user.id)
        invoices = await SubscriptionService.get_invoices(db, current_user.id)
        
        return {
            "status": "success",
            "subscription": {
                "plan_name": sub.plan_name if sub else "FREE",
                "status": sub.status if sub else "ACTIVE",
                "end_date": sub.end_date.isoformat() if (sub and sub.end_date) else None,
                "subscription_id": sub.id if sub else None
            },
            "invoices": [{
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": inv.amount,
                "total_amount": inv.total_amount,
                "status": inv.status,
                "created_at": inv.created_at.strftime("%Y-%m-%d")
            } for inv in invoices]
        }
    except Exception as e:
        logger.error(f"Failed to fetch subscription dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscription/checkout")
async def create_subscription_checkout(
    plan_name: str = Query(..., description="PRO or ELITE"),
    coupon_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        session_data = await SubscriptionService.create_checkout_session(db, current_user.id, plan_name.upper(), coupon_code)
        return {"status": "success", "session": session_data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscription/verify")
async def verify_subscription_payment(
    subscription_id: int = Query(...),
    razorpay_payment_id: str = Query(...),
    razorpay_signature: str = Query("mock_sig"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        verification = await SubscriptionService.verify_payment(
            db, current_user.id, subscription_id, razorpay_payment_id, razorpay_signature
        )
        return verification
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscription/verify-coupon/{coupon_code}")
async def verify_coupon(
    coupon_code: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        from models_saas import SaaSCoupon
        from datetime import datetime
        coupon_query = select(SaaSCoupon).where(
            SaaSCoupon.code == coupon_code.upper(),
            SaaSCoupon.is_active == True,
            SaaSCoupon.valid_until > datetime.utcnow()
        )
        coupon_res = await db.execute(coupon_query)
        coupon = coupon_res.scalars().first()
        if not coupon:
            return {"status": "error", "message": "Invalid or expired coupon code."}
        return {
            "status": "success",
            "code": coupon.code,
            "discount_pct": coupon.discount_pct
        }
    except Exception as e:
        logger.error(f"Coupon validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription/revenue")
async def get_billing_revenue_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Restrict to admins or Elite subscribers if needed, but allow all for testing
    try:
        analytics = await SubscriptionService.get_revenue_analytics(db)
        return {"status": "success", "analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── SMART MONEY CONCEPTS ROUTES ──────────────────────────────────────────────

@router.get("/smc")
async def get_smc_analysis(
    symbol: str = Query(..., description="NSE Stock Symbol"),
    timeframe: str = Query("1D", description="Timeframe: 5m, 15m, 30m, 1H, 1D"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate timeframe
    timeframe_upper = timeframe.upper()
    if timeframe_upper not in ("5M", "15M", "30M", "1H", "1D"):
        raise HTTPException(status_code=400, detail="Invalid timeframe. Supported: 5m, 15m, 30m, 1H, 1D")
        
    try:
        analysis = await SMCService.detect_smc_patterns(db, symbol, timeframe_upper)
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        logger.error(f"SMC analysis failed for {symbol} ({timeframe}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/smc/{symbol}")
async def get_smc_diagnostics(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Diagnostic endpoint: returns dataset alignment between live LTP and DB candles.
    Use this to verify whether the SMC engine is using the correct price dataset.
    """
    try:
        diag = await SMCService.get_diagnostics(db, symbol.upper())
        return {"status": "success", "diagnostics": diag}
    except Exception as e:
        logger.error(f"SMC diagnostics failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── PATTERN RECOGNITION ROUTES ───────────────────────────────────────────────

@router.get("/patterns")
async def get_pattern_recognition(
    symbol: str = Query(..., description="NSE Stock Symbol"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        patterns = await PatternRecognitionService.detect_patterns(db, symbol)
        return {"status": "success", "patterns": patterns}
    except Exception as e:
        logger.error(f"Pattern detection failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── LEARNING ACADEMY ROUTES ──────────────────────────────────────────────────

@router.get("/academy")
async def get_academy_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        courses = await AcademyService.get_courses(db, current_user.id)
        return {"status": "success", "courses": courses}
    except Exception as e:
        logger.error(f"Failed to fetch academy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/academy/course/{course_id}")
async def get_academy_course_details(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        details = await AcademyService.get_course_details(db, course_id, current_user.id)
        return {"status": "success", "course": details}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/academy/course/{course_id}/complete-lesson")
async def complete_academy_lesson(
    course_id: int,
    lesson_idx: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        completion = await AcademyService.mark_lesson_complete(db, current_user.id, course_id, lesson_idx)
        return {"status": "success", "progress": completion}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/academy/course/{course_id}/submit-quiz")
async def submit_academy_quiz(
    course_id: int,
    answers: List[int] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        results = await AcademyService.submit_quiz(db, current_user.id, course_id, answers)
        return {"status": "success", "result": results}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── BROKER AFFILIATE CENTER ROUTES ───────────────────────────────────────────

@router.get("/affiliate")
async def get_broker_affiliate_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        from models_saas import AffiliateTracker
        # Fetch or mock affiliate tracking information
        aff_query = select(AffiliateTracker).where(AffiliateTracker.user_id == current_user.id)
        aff_res = await db.execute(aff_query)
        trackers = aff_res.scalars().all()
        
        # If no trackers, create seeded tracking dashboard with zero metrics
        if not trackers:
            trackers = [
                AffiliateTracker(user_id=current_user.id, broker_name="UPSTOX", referral_code=f"REF_UP_{current_user.id}", clicks=0, conversions=0, total_commission=0.0),
                AffiliateTracker(user_id=current_user.id, broker_name="ZERODHA", referral_code=f"REF_ZD_{current_user.id}", clicks=0, conversions=0, total_commission=0.0),
            ]
            for t in trackers:
                db.add(t)
            await db.commit()
            
        return {
            "status": "success",
            "affiliates": [{
                "broker_name": t.broker_name,
                "referral_link": f"https://quantai.in/signup?ref={t.referral_code}",
                "clicks": t.clicks,
                "conversions": t.conversions,
                "commission": t.total_commission
            } for t in trackers]
        }
    except Exception as e:
        logger.error(f"Affiliate dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
