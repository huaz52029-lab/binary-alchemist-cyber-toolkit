"""IOC candidate extraction tool package."""

from modules.file_analysis.ioc.extractor import extract_iocs
from modules.file_analysis.ioc.tool import FileIocTool

__all__ = ["FileIocTool", "extract_iocs"]
