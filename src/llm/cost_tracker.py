"""Cost tracking for LLM usage across different model tiers."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from .router import ModelTier

logger = logging.getLogger(__name__)


# Pricing per 1M tokens (input/output) in USD
MODEL_COSTS = {
    ModelTier.ORCHESTRATOR: {"input": 15.0, "output": 75.0},  # Claude Opus 4.5
    ModelTier.REASONING: {"input": 0.27, "output": 1.10},     # DeepSeek-V3
    ModelTier.CODING: {"input": 0.14, "output": 0.28},        # DeepSeek-Coder-V2
    ModelTier.GENERAL: {"input": 0.15, "output": 0.60},       # Qwen-72B
    ModelTier.FAST: {"input": 0.06, "output": 0.24},          # Qwen-32B
}


@dataclass
class UsageRecord:
    """Record of a single LLM API call."""
    timestamp: datetime
    model: ModelTier
    input_tokens: int
    output_tokens: int
    cost: float
    session_id: str | None = None
    task: str | None = None


@dataclass
class SessionStats:
    """Aggregated statistics for a crawl session."""
    session_id: str
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    model_breakdown: dict[str, dict] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class CostTracker:
    """Tracks LLM usage and costs per session and globally."""

    def __init__(self):
        """Initialize cost tracker with empty state."""
        self.usage_records: list[UsageRecord] = []
        self.session_stats: dict[str, SessionStats] = {}
        self.global_total: float = 0.0

    def add(
        self,
        model: ModelTier,
        input_tokens: int,
        output_tokens: int,
        session_id: str | None = None,
        task: str | None = None,
    ) -> float:
        """
        Track a single LLM API call and return its cost.

        Args:
            model: Model tier used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            session_id: Optional session identifier
            task: Optional task name

        Returns:
            Cost in USD for this API call
        """
        # Calculate cost
        pricing = MODEL_COSTS[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Create usage record
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            session_id=session_id,
            task=task,
        )

        self.usage_records.append(record)
        self.global_total += total_cost

        # Update session stats if session_id provided
        if session_id:
            self._update_session_stats(record)

        logger.debug(
            f"Tracked {model.name}: {input_tokens} in + {output_tokens} out = "
            f"${total_cost:.6f}"
        )

        return total_cost

    def _update_session_stats(self, record: UsageRecord):
        """Update aggregated statistics for a session."""
        session_id = record.session_id

        if session_id not in self.session_stats:
            self.session_stats[session_id] = SessionStats(session_id=session_id)

        stats = self.session_stats[session_id]
        model_name = record.model.name

        # Update totals
        stats.total_cost += record.cost
        stats.total_input_tokens += record.input_tokens
        stats.total_output_tokens += record.output_tokens
        stats.total_requests += 1
        stats.updated_at = datetime.utcnow()

        # Update model breakdown
        if model_name not in stats.model_breakdown:
            stats.model_breakdown[model_name] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }

        breakdown = stats.model_breakdown[model_name]
        breakdown["requests"] += 1
        breakdown["input_tokens"] += record.input_tokens
        breakdown["output_tokens"] += record.output_tokens
        breakdown["cost"] += record.cost

    def get_session_cost(self, session_id: str) -> float:
        """
        Get total cost for a crawl session.

        Args:
            session_id: Session identifier

        Returns:
            Total cost in USD for the session
        """
        if session_id not in self.session_stats:
            return 0.0

        return self.session_stats[session_id].total_cost

    def get_session_stats(self, session_id: str) -> SessionStats | None:
        """
        Get full statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            SessionStats object or None if session not found
        """
        return self.session_stats.get(session_id)

    def get_breakdown(self, session_id: str) -> dict:
        """
        Get cost breakdown by model tier for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict mapping model tier names to usage stats
        """
        if session_id not in self.session_stats:
            return {}

        return self.session_stats[session_id].model_breakdown

    def get_global_stats(self) -> dict:
        """
        Get global statistics across all sessions.

        Returns:
            Dict with global usage and cost information
        """
        total_requests = len(self.usage_records)
        total_input_tokens = sum(r.input_tokens for r in self.usage_records)
        total_output_tokens = sum(r.output_tokens for r in self.usage_records)

        # Model breakdown
        model_breakdown = defaultdict(lambda: {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
        })

        for record in self.usage_records:
            model_name = record.model.name
            breakdown = model_breakdown[model_name]
            breakdown["requests"] += 1
            breakdown["input_tokens"] += record.input_tokens
            breakdown["output_tokens"] += record.output_tokens
            breakdown["cost"] += record.cost

        return {
            "total_cost": self.global_total,
            "total_requests": total_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_sessions": len(self.session_stats),
            "model_breakdown": dict(model_breakdown),
        }

    def get_cost_summary(self, session_id: str | None = None) -> str:
        """
        Generate a human-readable cost summary.

        Args:
            session_id: Optional session ID to get session-specific summary

        Returns:
            Formatted string with cost breakdown
        """
        if session_id:
            stats = self.get_session_stats(session_id)
            if not stats:
                return f"No data for session {session_id}"

            lines = [
                f"Session {session_id} Cost Summary:",
                f"  Total Cost: ${stats.total_cost:.4f}",
                f"  Total Requests: {stats.total_requests}",
                f"  Input Tokens: {stats.total_input_tokens:,}",
                f"  Output Tokens: {stats.total_output_tokens:,}",
                f"  Duration: {stats.updated_at - stats.started_at}",
                "",
                "Model Breakdown:",
            ]

            for model_name, breakdown in stats.model_breakdown.items():
                lines.append(
                    f"  {model_name}: ${breakdown['cost']:.4f} "
                    f"({breakdown['requests']} requests, "
                    f"{breakdown['input_tokens']:,} in, "
                    f"{breakdown['output_tokens']:,} out)"
                )

            return "\n".join(lines)

        else:
            # Global summary
            global_stats = self.get_global_stats()

            lines = [
                "Global Cost Summary:",
                f"  Total Cost: ${global_stats['total_cost']:.4f}",
                f"  Total Requests: {global_stats['total_requests']}",
                f"  Total Sessions: {global_stats['total_sessions']}",
                f"  Input Tokens: {global_stats['total_input_tokens']:,}",
                f"  Output Tokens: {global_stats['total_output_tokens']:,}",
                "",
                "Model Breakdown:",
            ]

            for model_name, breakdown in global_stats["model_breakdown"].items():
                lines.append(
                    f"  {model_name}: ${breakdown['cost']:.4f} "
                    f"({breakdown['requests']} requests, "
                    f"{breakdown['input_tokens']:,} in, "
                    f"{breakdown['output_tokens']:,} out)"
                )

            return "\n".join(lines)

    def reset_session(self, session_id: str):
        """
        Clear statistics for a specific session.

        Args:
            session_id: Session to reset
        """
        if session_id in self.session_stats:
            # Subtract from global total
            self.global_total -= self.session_stats[session_id].total_cost

            # Remove session stats
            del self.session_stats[session_id]

            # Remove usage records for this session
            self.usage_records = [
                r for r in self.usage_records
                if r.session_id != session_id
            ]

            logger.info(f"Reset session {session_id}")

    def reset_all(self):
        """Clear all tracking data."""
        self.usage_records.clear()
        self.session_stats.clear()
        self.global_total = 0.0
        logger.info("Reset all cost tracking data")

    def export_session_records(
        self,
        session_id: str,
        format: str = "dict"
    ) -> list[dict]:
        """
        Export usage records for a session.

        Args:
            session_id: Session identifier
            format: Export format ('dict' or 'csv')

        Returns:
            List of record dicts suitable for export

        Note:
            CSV format support can be added later if needed.
        """
        session_records = [
            r for r in self.usage_records
            if r.session_id == session_id
        ]

        if format == "dict":
            return [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "model": r.model.name,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost": r.cost,
                    "task": r.task,
                }
                for r in session_records
            ]
        else:
            raise ValueError(f"Unsupported format: {format}")
