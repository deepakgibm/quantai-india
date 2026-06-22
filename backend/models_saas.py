"""
QuantAI India SaaS Module - Database Models

Defines the persistent schema for:
1. Subscriptions & Invoicing (Razorpay Integration helper details)
2. Learning Academy (Courses, Quizzes, Certificates, Progress)
3. Research Center (Newsletters & Reports)
4. Affiliate Broker Center (Referral logs)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class SaaSSubscription(Base):
    """
    Tracks active user subscriptions, plans, and Razorpay links.
    """
    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_name = Column(String(50), nullable=False, default="FREE")  # FREE, PRO, ELITE
    status = Column(String(30), nullable=False, default="ACTIVE")    # ACTIVE, EXPIRED, CANCELLED
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    razorpay_subscription_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="saas_subscriptions")

    def __repr__(self):
        return f"<SaaSSubscription(user_id={self.user_id}, plan={self.plan_name}, status={self.status})>"

class SaaSInvoice(Base):
    """
    Stores structured transaction and invoice information (with GST and Coupons details).
    """
    __tablename__ = "saas_invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("saas_subscriptions.id"), nullable=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    cgst = Column(Float, default=0.0)  # 9% CGST for India
    sgst = Column(Float, default=0.0)  # 9% SGST for India
    discount = Column(Float, default=0.0)
    coupon_code = Column(String(50), nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default="PAID")  # PAID, PENDING, FAILED
    payment_method = Column(String(50), default="RAZORPAY")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="saas_invoices")
    subscription = relationship("SaaSSubscription", backref="saas_invoices")

    def __repr__(self):
        return f"<SaaSInvoice(invoice={self.invoice_number}, amount={self.total_amount}, status={self.status})>"

class SaaSCoupon(Base):
    """
    Coupons for promotional pricing discounts.
    """
    __tablename__ = "saas_coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_pct = Column(Float, nullable=False)  # Discount percentage (e.g. 10.0 for 10% off)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SaaSCoupon(code={self.code}, discount={self.discount_pct}%)>"

class SaaSReferral(Base):
    """
    Tracks platform referrals and associated marketing stats.
    """
    __tablename__ = "saas_referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    reward_points = Column(Integer, default=100)
    status = Column(String(30), default="PENDING")  # PENDING, CONVERTED
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], backref="referrals_sent")
    referred = relationship("User", foreign_keys=[referred_id], backref="referral_received")

    def __repr__(self):
        return f"<SaaSReferral(referrer={self.referrer_id}, referred={self.referred_id}, status={self.status})>"

class AcademyCourse(Base):
    """
    Pre-packaged trading education and courses.
    """
    __tablename__ = "academy_courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(50), default="Beginner")  # Beginner, Intermediate, Advanced
    duration_hours = Column(Float, default=1.0)
    is_premium = Column(Boolean, default=False)
    lessons = Column(JSON, nullable=True)  # List of objects: [{"title": "X", "video_url": "Y"}]
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AcademyCourse(title={self.title}, level={self.level})>"

class AcademyQuiz(Base):
    """
    Quizzes associated with Academy Courses.
    """
    __tablename__ = "academy_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    questions = Column(JSON, nullable=True)  # [{"question": "...", "options": [...], "answer_idx": 0}]
    passing_score = Column(Float, default=70.0)

    # Relationships
    course = relationship("AcademyCourse", backref="quizzes")

class AcademyProgress(Base):
    """
    Tracks users' completion of courses and scores.
    """
    __tablename__ = "academy_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    completed_lessons = Column(JSON, default=list)  # List of indices of completed lessons
    quiz_score = Column(Float, nullable=True)
    completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="academy_progress")
    course = relationship("AcademyCourse", backref="student_progress")

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uq_user_course_progress'),
    )

class AcademyCertificate(Base):
    """
    Certificates awarded for course completion.
    """
    __tablename__ = "academy_certificates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    certificate_hash = Column(String(100), unique=True, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="academy_certificates")
    course = relationship("AcademyCourse", backref="certificates_issued")

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uq_user_course_cert'),
    )

class ResearchReport(Base):
    """
    SaaS stock research reports & AI generated publications.
    """
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    report_type = Column(String(50), default="DAILY")  # DAILY, WEEKLY, AI_GENERATED
    summary = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ResearchReport(title={self.title}, type={self.report_type})>"

class AffiliateTracker(Base):
    """
    Broker affiliate listings, referral clicks, conversions, and commission dashboards.
    """
    __tablename__ = "affiliate_trackers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    broker_name = Column(String(50), nullable=False)  # UPSTOX, ZERODHA, ANGEL_ONE
    referral_code = Column(String(100), unique=True, nullable=False)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    total_commission = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="affiliate_trackers")

    __table_args__ = (
        UniqueConstraint('user_id', 'broker_name', name='uq_user_broker_affiliate'),
    )
