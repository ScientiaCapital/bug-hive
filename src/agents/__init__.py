"""Autonomous agents for web application testing."""

from src.agents.analyzer import PageAnalyzerAgent
from src.agents.classifier import BugClassifierAgent
from src.agents.crawler import CrawlerAgent

__all__ = [
    "CrawlerAgent",
    "PageAnalyzerAgent",
    "BugClassifierAgent",
]
