"""Prompt templates for BugHive LLM tasks.

This module will contain structured prompt templates for different agent tasks:
- Orchestration prompts (for Claude Opus)
- Analysis prompts (for DeepSeek-V3)
- Code analysis prompts (for DeepSeek-Coder)
- General task prompts (for Qwen models)

Prompts will be implemented in future development waves as agent capabilities
are built out.

Example structure:
    ORCHESTRATOR_PROMPTS = {
        "plan_crawl_strategy": "...",
        "quality_gate": "...",
    }

    ANALYSIS_PROMPTS = {
        "analyze_page": "...",
        "classify_bug": "...",
    }
"""

# Placeholder - prompts will be added as agent tasks are implemented
ORCHESTRATOR_PROMPTS = {}
ANALYSIS_PROMPTS = {}
CODING_PROMPTS = {}
GENERAL_PROMPTS = {}

__all__ = [
    "ORCHESTRATOR_PROMPTS",
    "ANALYSIS_PROMPTS",
    "CODING_PROMPTS",
    "GENERAL_PROMPTS",
]
