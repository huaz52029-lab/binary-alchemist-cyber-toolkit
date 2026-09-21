"""PE analysis tool package."""

from modules.file_analysis.pe_analysis.pe import analyze_pe
from modules.file_analysis.pe_analysis.tool import PeAnalysisTool

__all__ = ["PeAnalysisTool", "analyze_pe"]
