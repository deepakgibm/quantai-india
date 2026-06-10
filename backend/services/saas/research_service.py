"""
Research Center Report Ingestion and AI Generation Service
"""

import logging
from sqlalchemy.future import select
from models_saas import ResearchReport
from database import AsyncSessionLocal
from services.ai.provider import get_ai_provider
from config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

REPORTS_TO_SEED = [
    {
        "title": "Daily Market Digest - Bullish Breakouts in Energy Sector",
        "report_type": "DAILY",
        "summary": "Nifty holds key 20-day EMA support. Volume spikes detected in Reliance and Power Grid. Sector rotation points towards defensive expansion.",
        "content_markdown": """# Daily Market Digest: Energy Breakouts

Nifty indices closed in the green today, testing key support levels before bouncing back. The primary driver of momentum was the Energy sector.

## Technical Highlights
- **Nifty 50**: Tested 22,100 support and bounced back to close near 22,250.
- **RSI Overlays**: Multiple energy stock RSI metrics rebounded from oversold levels (35-40).
- **Volume Ratio**: Combined volume in Reliance and Power Grid exceeded 2.2x the 20-day SMA, indicating accumulation.

## Actionable Takeaways
1. Consider entering long positions in energy counters on minor consolidations.
2. Maintain strict trailing stop-losses below the 20-day EMA.
"""
    },
    {
        "title": "Weekly Macro Outlook - Monsoon Projections and Rural FMCG Demand",
        "report_type": "WEEKLY",
        "summary": "Detailed analysis of monsoon forecasts across central India and expected demand recovery in rural consumer staples (FMCG).",
        "content_markdown": """# Weekly Macro Outlook: Rural FMCG Demand Recovery

This week we explore the macroeconomic impact of positive monsoon forecasts on the FMCG sector.

## Rural Growth Indicators
- Rural consumer spending has grown at 6.4% YoY in the last quarter.
- Distribution networks have expanded by 8% across central states.
- High-frequency indicators suggest structural demand stabilization.

## Long Term Recommendations
- Focus on defensive sector leaders with stable margins and dividend yields.
"""
    }
]

class ResearchService:
    @staticmethod
    async def get_reports(db_session):
        """Fetch all available research reports from the archive."""
        query = select(ResearchReport).order_by(ResearchReport.created_at.desc())
        res = await db_session.execute(query)
        reports = res.scalars().all()
        
        # Seed reports if database is empty
        if not reports:
            await ResearchService._seed_reports(db_session)
            res = await db_session.execute(query)
            reports = res.scalars().all()
            
        return [{
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "summary": r.summary,
            "content_markdown": r.content_markdown,
            "pdf_url": r.pdf_url,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in reports]

    @staticmethod
    async def generate_ai_report(db_session, topic: str):
        """Use Gemini AI to dynamically compile a stock/sector research report."""
        title = f"AI Research: {topic}"
        summary = f"Automated technical and fundamental analysis report covering: {topic}."
        
        content = ""
        if not settings.ENABLE_AI_FEATURES or settings.MOCK_AI_RESPONSES:
            content = f"""# AI Research Report: {topic}

*Generated via QuantAI Copilot on {datetime.utcnow().strftime('%Y-%m-%d')}*

## Market Overview
Current indicators point to neutral-to-bullish structures for {topic}. 

## Technical Setup
- **Support Levels**: Key support established around 20-day moving averages.
- **RSI Indicators**: Momentum is cooling off from overbought conditions, preparing for next expansion.

## Strategic Outlook
Recommend accumulating position increments on dips, avoiding major lumpsum purchases at local resistance levels.
"""
        else:
            provider = get_ai_provider()
            prompt = f"""You are an institutional financial analyst. Generate a comprehensive stock/sector research report for: '{topic}'.
Structure the report with markdown formatting, including:
1. Title and Executive Summary
2. Key Technical Indicators (RSI, MACD, Volume Profile)
3. Fundamental Valuation (P/E, margins, growth projections)
4. Strategic Investment Recommendations (Buy zones, Target, Stop Loss)

Keep the report concise, highly professional, and do not use generic placeholders. Only NSE segment contexts."""

            try:
                content = await provider.generate_content(prompt)
                # Split first lines to extract summary
                lines = [line.strip() for line in content.split("\n") if len(line.strip()) > 5]
                if len(lines) > 2:
                    summary = lines[1][:200] if not lines[1].startswith("#") else lines[2][:200]
            except Exception as e:
                logger.error(f"Failed to generate AI research report: {e}")
                content = f"Error generating automated AI report: {e}"
                
        # Create and persist report in DB
        report = ResearchReport(
            title=title,
            report_type="AI_GENERATED",
            summary=summary,
            content_markdown=content
        )
        db_session.add(report)
        await db_session.commit()
        
        return {
            "id": report.id,
            "title": report.title,
            "report_type": report.report_type,
            "summary": report.summary,
            "content_markdown": report.content_markdown,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }

    @staticmethod
    async def _seed_reports(db_session):
        """Seeds initial default reports into database."""
        logger.info("Pre-seeding Research Archive reports...")
        for r_data in REPORTS_TO_SEED:
            report = ResearchReport(
                title=r_data["title"],
                report_type=r_data["report_type"],
                summary=r_data["summary"],
                content_markdown=r_data["content_markdown"]
            )
            db_session.add(report)
        await db_session.commit()
