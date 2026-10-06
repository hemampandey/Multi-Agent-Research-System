from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import xml.sax.saxutils as saxutils

def create_pdf_buffer(report_text):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = []
    for line in report_text.split("\n"):
        # Escape XML-like special characters (e.g., <, >, &) to prevent ReportLab crash
        escaped_line = saxutils.escape(line)
        content.append(Paragraph(escaped_line, styles["Normal"]))

    doc.build(content)
    buffer.seek(0)
    return buffer