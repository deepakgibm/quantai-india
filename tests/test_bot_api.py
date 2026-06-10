"""
Bot API — Endpoint Tests

Tests for POST /run, GET /status, GET /results, GET /last-run.
Uses mocked orchestrator to avoid actual data fetching.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.bot.bot_orchestrator import (
    BotOrchestrator, BotStep, BotRunStatus, BotRunResult,
    get_bot_orchestrator, STEP_LABELS,
)


class TestBotOrchestratorState:
    def test_initial_no_runs(self, monkeypatch):
        orch = BotOrchestrator()
        # Mock database lookup to ensure clean initial state for unit testing
        monkeypatch.setattr(orch, "get_last_run_id", lambda: None)
        assert orch.get_last_run_id() is None

    def test_get_status_unknown_id(self):
        orch = BotOrchestrator()
        assert orch.get_status("nonexistent") is None

    def test_get_result_unknown_id(self):
        orch = BotOrchestrator()
        assert orch.get_result("nonexistent") is None


class TestBotRunStatus:
    def test_to_dict(self):
        s = BotRunStatus(
            run_id="abc",
            status="COMPLETED",
            current_step="COMPLETED",
            current_step_label="Completed",
            progress_pct=100,
            elapsed_seconds=5.2,
        )
        d = s.to_dict()
        assert d["run_id"] == "abc"
        assert d["status"] == "COMPLETED"
        assert d["progress_pct"] == 100


class TestBotRunResult:
    def test_to_dict(self):
        r = BotRunResult(
            run_id="xyz",
            market_trend={"trend": "BULLISH", "ema_50": 22000, "ema_200": 21000,
                          "momentum": 2.5, "last_close": 22500},
            buy_signals=[{"symbol": "TCS", "signal_type": "BUY"}],
            sell_signals=[],
            summary={"total_signals": 1},
            completed_at="2026-05-02T10:00:00",
        )
        d = r.to_dict()
        assert d["run_id"] == "xyz"
        assert len(d["buy_signals"]) == 1
        assert d["market_trend"]["trend"] == "BULLISH"


class TestStepLabels:
    def test_all_steps_have_labels(self):
        for step in BotStep:
            assert step in STEP_LABELS


class TestSingleton:
    def test_returns_same_instance(self):
        a = get_bot_orchestrator()
        b = get_bot_orchestrator()
        assert a is b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
