"""Export the report DOCX to PDF with Microsoft Word and print the page count.

Word's own layout engine decides the page count, so the number printed here
is the one readers will see. Run on Windows with Word installed.
"""
import sys
from pathlib import Path

import win32com.client

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "CodeBridge_Project_Report.docx"
PDF = ROOT / "CodeBridge_Project_Report.pdf"

WD_STATISTIC_PAGES = 2
WD_EXPORT_FORMAT_PDF = 17

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)
    doc.Fields.Update()
    doc.Repaginate()
    pages = doc.ComputeStatistics(WD_STATISTIC_PAGES)
    doc.ExportAsFixedFormat(str(PDF), WD_EXPORT_FORMAT_PDF, OpenAfterExport=False,
                            OptimizeFor=0, CreateBookmarks=1, DocStructureTags=True)
    doc.Close(SaveChanges=False)
finally:
    word.Quit()

import fitz  # noqa: E402

pdf_pages = fitz.open(PDF).page_count
print(f"Word page count: {pages}; PDF page count: {pdf_pages}")
sys.exit(0 if pages == pdf_pages == 10 else 1)
