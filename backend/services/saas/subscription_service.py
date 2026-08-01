"""
SaaS Subscription, Invoicing, and Billing Service
"""

import logging
from datetime import datetime, timedelta
import random
from sqlalchemy.future import select
from sqlalchemy import func
from models import User
from models_saas import SaaSSubscription, SaaSInvoice, SaaSCoupon, SaaSReferral

logger = logging.getLogger(__name__)

# Plan price configuration (in INR)
PLAN_PRICES = {
    "FREE": 0.0,
    "PRO": 999.0,
    "ELITE": 2999.0
}

class SubscriptionService:
    @staticmethod
    async def get_active_subscription(db_session, user_id: int):
        """Fetch the current active subscription of the user."""
        query = select(SaaSSubscription).where(
            SaaSSubscription.user_id == user_id,
            SaaSSubscription.status == "ACTIVE"
        ).order_by(SaaSSubscription.created_at.desc())
        
        result = await db_session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_invoices(db_session, user_id: int):
        """Fetch all invoices for the user."""
        query = select(SaaSInvoice).where(
            SaaSInvoice.user_id == user_id
        ).order_by(SaaSInvoice.created_at.desc())
        
        result = await db_session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create_checkout_session(db_session, user_id: int, plan_name: str, coupon_code: str = None):
        """Simulates Razorpay checkout session creation."""
        if plan_name not in PLAN_PRICES:
            raise ValueError(f"Invalid plan name: {plan_name}")
            
        base_price = PLAN_PRICES[plan_name]
        discount = 0.0
        
        # Validate and apply coupon
        if coupon_code:
            coupon_query = select(SaaSCoupon).where(
                SaaSCoupon.code == coupon_code.upper(),
                SaaSCoupon.is_active == True,
                SaaSCoupon.valid_until > datetime.utcnow()
            )
            coupon_res = await db_session.execute(coupon_query)
            coupon = coupon_res.scalars().first()
            if coupon:
                discount = base_price * (coupon.discount_pct / 100.0)
            else:
                logger.warning(f"Coupon code {coupon_code} is invalid or expired.")
                
        discounted_price = max(0.0, base_price - discount)
        
        # GST Calculations (18% for Indian financial services: 9% CGST + 9% SGST)
        cgst = discounted_price * 0.09
        sgst = discounted_price * 0.09
        total_amount = discounted_price + cgst + sgst
        
        # Create a pending subscription record
        razorpay_sub_id = f"sub_sim_{random.randint(100000, 999999)}"
        subscription = SaaSSubscription(
            user_id=user_id,
            plan_name=plan_name,
            status="PENDING",
            razorpay_subscription_id=razorpay_sub_id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30)
        )
        
        db_session.add(subscription)
        await db_session.flush()
        
        # Create an invoice model mapping to this checkout
        invoice_num = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        invoice = SaaSInvoice(
            user_id=user_id,
            subscription_id=subscription.id,
            invoice_number=invoice_num,
            amount=base_price,
            cgst=cgst,
            sgst=sgst,
            discount=discount,
            coupon_code=coupon_code,
            total_amount=total_amount,
            status="PENDING"
        )
        
        db_session.add(invoice)
        await db_session.commit()
        
        return {
            "subscription_id": subscription.id,
            "razorpay_subscription_id": razorpay_sub_id,
            "total_amount": total_amount,
            "invoice_number": invoice_num
        }

    @staticmethod
    async def verify_payment(db_session, user_id: int, subscription_id: int, razorpay_payment_id: str, razorpay_signature: str = "mock_sig"):
        """Verify payment and update user subscription status."""
        sub_query = select(SaaSSubscription).where(
            SaaSSubscription.id == subscription_id,
            SaaSSubscription.user_id == user_id
        )
        sub_res = await db_session.execute(sub_query)
        subscription = sub_res.scalars().first()
        
        if not subscription:
            raise ValueError("Subscription record not found.")
            
        # Cryptographic signature verification
        import hmac
        import hashlib
        import os
        from config import settings
        
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret")
        
        # Razorpay signature format check: payment_id + "|" + subscription_id
        message = f"{razorpay_payment_id}|{subscription.razorpay_subscription_id}"
        expected_signature = hmac.new(
            razorpay_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        is_dev = settings.ENVIRONMENT == "development" or getattr(settings, "SAFE_MODE", False) or os.getenv("SAFE_MODE") == "true"
        
        if razorpay_signature == "mock_sig" and is_dev:
            logger.warning("[Razorpay] Accepting mock_sig in development mode.")
        else:
            if not hmac.compare_digest(expected_signature, razorpay_signature):
                raise ValueError("Invalid Razorpay payment signature.")
            
        # Update subscription state to ACTIVE
        subscription.status = "ACTIVE"
        subscription.start_date = datetime.utcnow()
        subscription.end_date = datetime.utcnow() + timedelta(days=30)
        
        # Sync to user subscription level
        user_query = select(User).where(User.id == user_id)
        user_res = await db_session.execute(user_query)
        user = user_res.scalars().first()
        if user:
            user.subscription_level = subscription.plan_name
            
        # Update associated invoice state to PAID
        inv_query = select(SaaSInvoice).where(
            SaaSInvoice.subscription_id == subscription_id,
            SaaSInvoice.user_id == user_id
        )
        inv_res = await db_session.execute(inv_query)
        invoice = inv_res.scalars().first()
        if invoice:
            invoice.status = "PAID"
            
        # Check and convert any referral status
        ref_query = select(SaaSReferral).where(
            SaaSReferral.referred_id == user_id,
            SaaSReferral.status == "PENDING"
        )
        ref_res = await db_session.execute(ref_query)
        referral = ref_res.scalars().first()
        if referral:
            referral.status = "CONVERTED"
            referral.reward_points = 500  # Grant referral bonus
            
        await db_session.commit()
        return {
            "status": "success",
            "subscription_id": subscription.id,
            "plan": subscription.plan_name,
            "expiry": subscription.end_date.isoformat()
        }

    @staticmethod
    async def get_revenue_analytics(db_session):
        """Fetch key revenue performance stats."""
        # Query total active subscriptions
        active_sub_query = select(func.count(SaaSSubscription.id), SaaSSubscription.plan_name).where(
            SaaSSubscription.status == "ACTIVE"
        ).group_by(SaaSSubscription.plan_name)
        active_sub_res = await db_session.execute(active_sub_query)
        active_counts = {plan: count for count, plan in active_sub_res.all()}
        
        # Total revenue collected
        rev_query = select(func.sum(SaaSInvoice.total_amount)).where(SaaSInvoice.status == "PAID")
        rev_res = await db_session.execute(rev_query)
        total_revenue = rev_res.scalar() or 0.0
        
        # Total GST collected
        gst_query = select(func.sum(SaaSInvoice.cgst + SaaSInvoice.sgst)).where(SaaSInvoice.status == "PAID")
        gst_res = await db_session.execute(gst_query)
        total_gst = gst_res.scalar() or 0.0
        
        return {
            "active_subscriptions": active_counts,
            "total_revenue": total_revenue,
            "total_gst": total_gst,
            "arpu": total_revenue / max(1, sum(active_counts.values()))
        }

    @staticmethod
    async def seed_coupons(db_session):
        """Seed default coupons in the database if they don't exist."""
        from datetime import datetime, timedelta
        from models_saas import SaaSCoupon
        
        coupons = [
            {"code": "WELCOME10", "discount_pct": 10.0, "valid_until": datetime.utcnow() + timedelta(days=365), "is_active": True},
            {"code": "QUANT20", "discount_pct": 20.0, "valid_until": datetime.utcnow() + timedelta(days=365), "is_active": True}
        ]
        
        for c in coupons:
            q = select(SaaSCoupon).where(SaaSCoupon.code == c["code"])
            res = await db_session.execute(q)
            existing = res.scalars().first()
            if not existing:
                db_coupon = SaaSCoupon(
                    code=c["code"],
                    discount_pct=c["discount_pct"],
                    valid_until=c["valid_until"],
                    is_active=c["is_active"]
                )
                db_session.add(db_coupon)
        await db_session.commit()

