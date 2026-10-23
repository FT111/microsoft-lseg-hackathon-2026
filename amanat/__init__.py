"""Modular Shariah stock analysis components."""

from .analyser import OpenAIInferenceClient, StockAnalyser
from .models import AnalysisResult, Document, ScreenStatus, Stock
from .sources import (
    AutomaticDocumentProvider,
    GlobalIssuerDocumentProvider,
    SecEdgarDocumentProvider,
    TrustedWebSearchProvider,
)

__all__ = [
    "AnalysisResult",
    "AutomaticDocumentProvider",
    "Document",
    "GlobalIssuerDocumentProvider",
    "OpenAIInferenceClient",
    "ScreenStatus",
    "SecEdgarDocumentProvider",
    "TrustedWebSearchProvider",
    "Stock",
    "StockAnalyser",
]
