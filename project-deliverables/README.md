# CodeBridge: project deliverables

| File | Contents |
|---|---|
| [CodeBridge_Project_Report.docx](CodeBridge_Project_Report.docx) | Editable academic report, 10 pages (A4) |
| [CodeBridge_Project_Report.pdf](CodeBridge_Project_Report.pdf) | PDF export of the report from Microsoft Word, 10 pages |
| [CodeBridge_Presentation.pptx](CodeBridge_Presentation.pptx) | Editable presentation: 15 slides, 16:9, with speaker notes |

Before submitting, fill in the placeholders on the report cover and on slides 1 and 15: `[Student Name]`, `[Roll Number]`, `[Department]`, `[Institution]`, `[Guide Name]` and `[Academic Year]`.

## Sources of the figures

- **`assets/screenshots/live-*.png`:**
  - captured on 13 October 2026 from the live deployment at https://codebridge-swart.vercel.app;
  - captured with headless Microsoft Edge, at 1440×900 at 2× scale (the phone view at 500 px wide);
  - deep links of the form `?example=<id>&tab=<tab>` selected each view.
- **`assets/screenshots/crops/`:** the same captures, trimmed to one panel by `build/crops.py`. Nothing is drawn or edited.
- **`assets/diagrams/`:** drawn by `build/diagrams.py` from the actual modules in `frontend/src` and `backend/app`.
- **Code samples, TAC listings and optimization counts:** these are unedited compiler output.

## Rebuilding

The build needs Windows with Microsoft Word and PowerPoint, which are used for the PDF export, the page count and the slide rendering. It also needs a Python environment with these packages:

```text
python-docx==1.2.0
python-pptx==1.0.2
matplotlib==3.10.7
pymupdf==1.26.5
pywin32==311
```

Run these commands from `project-deliverables/build`:

```powershell
python diagrams.py        # assets/diagrams/*.png
python crops.py           # assets/screenshots/crops/*.png
python build_report.py    # CodeBridge_Project_Report.docx
python export_report.py   # PDF via Word; exits non-zero unless both counts are 10 pages
python build_slides.py    # CodeBridge_Presentation.pptx (asserts 15 slides)
python render_slides.py <dir>   # PNG of every slide via PowerPoint, for visual review
```
