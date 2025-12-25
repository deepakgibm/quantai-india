
from typing import List, Dict, Any
from .research_agent import ResearchAgent
from .risk_agent import RiskAgent
from .decision_agent import DecisionAgent

class AgentOrchestrator:
    """
    Coordinates the 3-Agent Workflow.
    """
    
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.risk_agent = RiskAgent()
        self.decision_agent = DecisionAgent()
        
    async def run_workflow(self, prompt: str) -> Dict[str, Any]:
        """
        Parses prompt and runs the agents.
        """
        print(f"🤖 Orchestrator received: '{prompt}'")
        
        # 0. Parse Prompt (Simple keyword extraction for now)
        # In future, use LLM to parse intent
        symbols = await self._get_target_symbols(prompt)
        
        # 1. Research Agent
        research_results = await self.research_agent.analyze(symbols)
        
        # 2. Risk Agent
        risk_results = await self.risk_agent.analyze(research_results)
        
        # 3. Decision Agent
        final_results = await self.decision_agent.decide(research_results, risk_results)
        
        # Return top 10
        return {
            "status": "success",
            "data": final_results[:10],
            "meta": {
                "total_analyzed": len(symbols),
                "prompt": prompt
            }
        }
        
    async def _get_target_symbols(self, prompt: str) -> List[str]:
        # If user specifies stocks, use them. Else default to Nifty 50/200 subset.
        # For demo speed, pick random 20 from Nifty 200
        client = self.research_agent.client
        all_symbols = await client.get_nifty_200_symbols()
        
        # Just take top 5 for speed
        return [s for s, k in all_symbols[:5]]
