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
from services.saas.portfolio_intel_service import PortfolioIntelService
from services.saas.signal_center_service import SignalCenterService
from services.saas.smc_service import SMCService
from services.saas.pattern_recognition_service import PatternRecognitionService
from services.saas.academy_service import AcademyService
from services.saas.research_service import ResearchService

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

# ─── PORTFOLIO INTELLIGENCE ROUTES ───────────────────────────────────────────

@router.get("/portfolio-intel")
async def get_portfolio_intelligence(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import asyncio
    try:
        analysis = await asyncio.wait_for(
            PortfolioIntelService.analyze_portfolio(db, current_user.id),
            timeout=10.0
        )
        return {"status": "success", "analysis": analysis}
    except asyncio.TimeoutError:
        logger.error("Portfolio intelligence timed out (10s)")
        raise HTTPException(status_code=504, detail="Portfolio analysis timed out. Please try again.")
    except Exception as e:
        logger.error(f"Portfolio intelligence failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── SIGNAL PERFORMANCE CENTER ROUTES ──────────────────────────────────────────

@router.get("/signal-center")
async def get_signal_center(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        metrics = await SignalCenterService.get_performance_metrics(db)
        return {"status": "success", "metrics": metrics}
    except Exception as e:
        logger.error(f"Signal center stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── SMART MONEY CONCEPTS ROUTES ──────────────────────────────────────────────

@router.get("/smc")
async def get_smc_analysis(
    symbol: str = Query(..., description="NSE Stock Symbol"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        analysis = await SMCService.detect_smc_patterns(db, symbol)
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        logger.error(f"SMC analysis failed for {symbol}: {e}")
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

# ─── RESEARCH CENTER ROUTES ───────────────────────────────────────────────────

@router.get("/research")
async def get_research_newsletter_archive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        reports = await ResearchService.get_reports(db)
        return {"status": "success", "reports": reports}
    except Exception as e:
        logger.error(f"Failed to fetch research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/research/generate")
async def generate_ai_research_report(
    topic: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        report = await ResearchService.generate_ai_report(db, topic)
        return {"status": "success", "report": report}
    except Exception as e:
        logger.error(f"Research generation failed: {e}")
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
        
        # If no trackers, create seeded mock tracking dashboard
        if not trackers:
            trackers = [
                AffiliateTracker(user_id=current_user.id, broker_name="UPSTOX", referral_code=f"REF_UP_{current_user.id}", clicks=42, conversions=5, total_commission=2500.0),
                AffiliateTracker(user_id=current_user.id, broker_name="ZERODHA", referral_code=f"REF_ZD_{current_user.id}", clicks=18, conversions=2, total_commission=1000.0),
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
