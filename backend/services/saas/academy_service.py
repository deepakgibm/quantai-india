"""
Learning Academy Course & Quiz Service
"""

import logging
import uuid
from sqlalchemy.future import select
from models_saas import AcademyCourse, AcademyQuiz, AcademyProgress, AcademyCertificate
from database import AsyncSessionLocal
from datetime import datetime

logger = logging.getLogger(__name__)

COURSES_TO_SEED = [
    {
        "title": "Intro to Indian Stock Analysis",
        "description": "Learn the basics of fundamental analysis, reading balance sheets, and key ratios in the context of the NSE.",
        "level": "Beginner",
        "duration_hours": 3.5,
        "is_premium": False,
        "lessons": [
            {"title": "Understanding Financial Statements", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "Key Valuation Ratios (P/E, P/B, Debt/Equity)", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "How to Track Corporate Disclosures", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"}
        ]
    },
    {
        "title": "Order Flow & Smart Money Trading",
        "description": "Master Liquidity Zones, Order Blocks, and BOS/CHOCH structural shift mechanics.",
        "level": "Intermediate",
        "duration_hours": 6.0,
        "is_premium": True,
        "lessons": [
            {"title": "Anatomy of an Order Block", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "Identifying Fair Value Gaps (FVG)", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "SMC Entry Models", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"}
        ]
    },
    {
        "title": "Quantitative Risk & Money Management",
        "description": "Design systematic backtesting configurations and implement position sizing formulas.",
        "level": "Advanced",
        "duration_hours": 5.0,
        "is_premium": True,
        "lessons": [
            {"title": "Position Sizing Matrix", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "Sharpe & Drawdown Optimisation", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"},
            {"title": "Walk-forward Parameter Tuning", "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ"}
        ]
    }
]

QUIZZES_TO_SEED = [
    {
        "questions": [
            {"question": "What does P/E ratio stand for?", "options": ["Price to Equity", "Price to Earnings", "Profit to Earnings"], "answer_idx": 1},
            {"question": "Which ratio measures a firm's leverage?", "options": ["Debt to Equity", "ROE", "ROCE"], "answer_idx": 0}
        ],
        "passing_score": 50.0
    },
    {
        "questions": [
            {"question": "A bullish Fair Value Gap is created when:", "options": ["Candle 3 low is above Candle 1 high", "Candle 3 high is below Candle 1 low", "Candle 2 closes below its open"], "answer_idx": 0},
            {"question": "What does BOS stand for?", "options": ["Block of Shares", "Break of Structure", "Bullish Order Sequence"], "answer_idx": 1}
        ],
        "passing_score": 50.0
    },
    {
        "questions": [
            {"question": "If your stop-loss distance is Rs 20 and your risk is Rs 1000, what is the recommended quantity?", "options": ["50", "20", "10"], "answer_idx": 0}
        ],
        "passing_score": 100.0
    }
]

class AcademyService:
    @staticmethod
    async def get_courses(db_session, user_id: int):
        """Fetch all courses along with progress status for a specific user."""
        query = select(AcademyCourse)
        res = await db_session.execute(query)
        courses = res.scalars().all()
        
        # Seed courses if database is empty
        if not courses:
            await AcademyService._seed_academy(db_session)
            res = await db_session.execute(query)
            courses = res.scalars().all()
            
        result_list = []
        for course in courses:
            # Check user progress
            prog_query = select(AcademyProgress).where(
                AcademyProgress.user_id == user_id,
                AcademyProgress.course_id == course.id
            )
            prog_res = await db_session.execute(prog_query)
            progress = prog_res.scalars().first()
            
            # Check certificate status
            cert_query = select(AcademyCertificate).where(
                AcademyCertificate.user_id == user_id,
                AcademyCertificate.course_id == course.id
            )
            cert_res = await db_session.execute(cert_query)
            certificate = cert_res.scalars().first()
            
            progress_data = {
                "completed": progress.completed if progress else False,
                "completed_lessons": progress.completed_lessons if progress else [],
                "quiz_score": progress.quiz_score if progress else None,
                "certificate_hash": certificate.certificate_hash if certificate else None
            }
            
            result_list.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "level": course.level,
                "duration_hours": course.duration_hours,
                "is_premium": course.is_premium,
                "lessons_count": len(course.lessons) if course.lessons else 0,
                "progress": progress_data
            })
            
        return result_list

    @staticmethod
    async def get_course_details(db_session, course_id: int, user_id: int):
        """Fetch full details, lessons list, and quiz configuration for a course."""
        course_query = select(AcademyCourse).where(AcademyCourse.id == course_id)
        course_res = await db_session.execute(course_query)
        course = course_res.scalars().first()
        
        if not course:
            raise ValueError("Course not found.")
            
        # Get Quiz
        quiz_query = select(AcademyQuiz).where(AcademyQuiz.course_id == course_id)
        quiz_res = await db_session.execute(quiz_query)
        quiz = quiz_res.scalars().first()
        
        # Get Progress
        prog_query = select(AcademyProgress).where(
            AcademyProgress.user_id == user_id,
            AcademyProgress.course_id == course_id
        )
        prog_res = await db_session.execute(prog_query)
        progress = prog_res.scalars().first()
        
        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level,
            "lessons": course.lessons,
            "quiz": {
                "questions": quiz.questions if quiz else []
            } if quiz else None,
            "progress": {
                "completed_lessons": progress.completed_lessons if progress else [],
                "completed": progress.completed if progress else False,
                "quiz_score": progress.quiz_score if progress else None
            }
        }

    @staticmethod
    async def mark_lesson_complete(db_session, user_id: int, course_id: int, lesson_idx: int):
        """Mark a specific lesson as completed in user progress."""
        prog_query = select(AcademyProgress).where(
            AcademyProgress.user_id == user_id,
            AcademyProgress.course_id == course_id
        )
        prog_res = await db_session.execute(prog_query)
        progress = prog_res.scalars().first()
        
        if not progress:
            progress = AcademyProgress(
                user_id=user_id,
                course_id=course_id,
                completed_lessons=[]
            )
            db_session.add(progress)
            
        completed = list(progress.completed_lessons or [])
        if lesson_idx not in completed:
            completed.append(lesson_idx)
            progress.completed_lessons = completed
            
        await db_session.commit()
        return {"completed_lessons": completed}

    @staticmethod
    async def submit_quiz(db_session, user_id: int, course_id: int, answers: list):
        """Grade submitted quiz answers, mark course complete, and issue a certificate if passing."""
        # Fetch Quiz configuration
        quiz_query = select(AcademyQuiz).where(AcademyQuiz.course_id == course_id)
        quiz_res = await db_session.execute(quiz_query)
        quiz = quiz_res.scalars().first()
        
        if not quiz or not quiz.questions:
            raise ValueError("No quiz configured for this course.")
            
        total_questions = len(quiz.questions)
        correct_count = 0
        
        for idx, q in enumerate(quiz.questions):
            # check answer index matches
            if idx < len(answers) and answers[idx] == q["answer_idx"]:
                correct_count += 1
                
        score = (correct_count / total_questions) * 100.0
        passed = score >= quiz.passing_score
        
        # Update user course progress
        prog_query = select(AcademyProgress).where(
            AcademyProgress.user_id == user_id,
            AcademyProgress.course_id == course_id
        )
        prog_res = await db_session.execute(prog_query)
        progress = prog_res.scalars().first()
        
        if not progress:
            progress = AcademyProgress(user_id=user_id, course_id=course_id)
            db_session.add(progress)
            
        progress.quiz_score = score
        
        certificate_hash = None
        if passed:
            progress.completed = True
            
            # Generate Certificate hash if it doesn't exist
            cert_query = select(AcademyCertificate).where(
                AcademyCertificate.user_id == user_id,
                AcademyCertificate.course_id == course_id
            )
            cert_res = await db_session.execute(cert_query)
            cert = cert_res.scalars().first()
            
            if not cert:
                certificate_hash = f"CERT-{uuid.uuid4().hex[:12].upper()}"
                cert = AcademyCertificate(
                    user_id=user_id,
                    course_id=course_id,
                    certificate_hash=certificate_hash
                )
                db_session.add(cert)
            else:
                certificate_hash = cert.certificate_hash
                
        await db_session.commit()
        return {
            "score": score,
            "passed": passed,
            "certificate_hash": certificate_hash
        }

    @staticmethod
    async def _seed_academy(db_session):
        """Pre-seeds standard course modules into database."""
        logger.info("Pre-seeding Learning Academy courses and quizzes...")
        for idx, crs_data in enumerate(COURSES_TO_SEED):
            course = AcademyCourse(
                title=crs_data["title"],
                description=crs_data["description"],
                level=crs_data["level"],
                duration_hours=crs_data["duration_hours"],
                is_premium=crs_data["is_premium"],
                lessons=crs_data["lessons"]
            )
            db_session.add(course)
            await db_session.flush()
            
            # Seed matching quiz
            quiz_data = QUIZZES_TO_SEED[idx]
            quiz = AcademyQuiz(
                course_id=course.id,
                questions=quiz_data["questions"],
                passing_score=quiz_data["passing_score"]
            )
            db_session.add(quiz)
            
        await db_session.commit()
