from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from datetime import datetime as dt, timedelta

class ReportExporter:
    def __init__(self, log_manager):
        self.log_manager = log_manager

    def export_pdf(self, filename, start_date, end_date):
        """Export a PDF report for the given date range with an attractive design."""
        doc = SimpleDocTemplate(filename, pagesize=letter, 
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=1*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        styles.add(ParagraphStyle(name='Header', fontSize=16, leading=20, textColor=colors.white))
        styles.add(ParagraphStyle(name='SubHeader', fontSize=12, leading=14, textColor=colors.HexColor("#2DA44E")))
        styles.add(ParagraphStyle(name='NormalBold', fontName='Helvetica-Bold', fontSize=10, leading=12))
        styles.add(ParagraphStyle(name='Footer', fontSize=8, leading=10, textColor=colors.grey, alignment=1))

        # Header (colored bar with text)
        def header(canvas, doc):
            canvas.saveState()
            # Draw a colored bar across the top
            canvas.setFillColor(colors.HexColor("#0969DA"))
            canvas.rect(0, doc.pagesize[1] - 0.75*inch, doc.pagesize[0], 0.75*inch, fill=1, stroke=0)
            # Draw app name
            canvas.setFont('Helvetica-Bold', 18)
            canvas.setFillColor(colors.white)
            canvas.drawString(0.5*inch, doc.pagesize[1] - 0.5*inch, "Productivity Tracker Pro")
            canvas.restoreState()

        # Footer with tagline and page number
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#0969DA"))
            canvas.rect(0, 0, doc.pagesize[0], 0.5*inch, fill=1, stroke=0)
            page_num = canvas.getPageNumber()
            text = f"Track Smarter, Work Better | Page {page_num} | Generated on {dt.now().strftime('%Y-%m-%d %H:%M:%S')}"
            footer_p = Paragraph(text, styles['Footer'])
            w, h = footer_p.wrap(doc.pagesize[0] - 1*inch, 0.5*inch)
            footer_p.drawOn(canvas, 0.5*inch, 0.25*inch)
            canvas.restoreState()

        # Title
        title = Paragraph(f"Report Period: {start_date} to {end_date}", styles['SubHeader'])
        elements.append(title)
        elements.append(Spacer(1, 0.25*inch))

        # Fetch and aggregate data
        usage_data = self._aggregate_usage(start_date, end_date)
        print(f"Debug: Aggregated usage data: {usage_data}")

        # Summary: Total Tracked Time
        total_seconds = sum(usage_data.values())
        hours = int(total_seconds // 3600)  # Convert to int
        minutes = int((total_seconds % 3600) // 60)  # Convert to int
        secs = int(total_seconds % 60)  # Convert to int
        summary_text = f"Total Tracked Time: {hours:02d}h {minutes:02d}m {secs:02d}s"
        summary = Paragraph(summary_text, styles['SubHeader'])
        elements.append(summary)
        elements.append(Spacer(1, 0.25*inch))

        # Bar Chart
        if usage_data:
            drawing = Drawing(400, 200)
            bc = VerticalBarChart()
            bc.x = 50
            bc.y = 20
            bc.height = 150
            bc.width = 300
            bc.data = [list(usage_data.values())]
            bc.bars.fillColor = colors.HexColor("#0969DA")
            bc.bars.strokeColor = colors.HexColor("#3A4546")
            bc.strokeColor = colors.HexColor("#3A4546")
            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = max(usage_data.values()) * 1.2 if usage_data.values() else 1
            bc.valueAxis.labels.fontName = 'Helvetica'
            bc.valueAxis.labels.fontSize = 8
            bc.categoryAxis.labels.fontName = 'Helvetica'
            bc.categoryAxis.labels.fontSize = 8
            bc.categoryAxis.labels.angle = 45
            bc.categoryAxis.labels.boxAnchor = 'ne'
            bc.categoryAxis.categoryNames = list(usage_data.keys())
            bc.categoryAxis.labels.dx = -5
            bc.categoryAxis.labels.dy = -5
            drawing.add(bc)
            elements.append(Paragraph("Usage Distribution", styles['SubHeader']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(drawing)
            elements.append(Spacer(1, 0.25*inch))

        # Table
        if not usage_data:
            no_data = Paragraph("No usage data available for this period.", styles['Normal'])
            elements.append(no_data)
        else:
            data = [["Application", "Time Spent"]]
            for app, seconds in sorted(usage_data.items(), key=lambda x: x[1], reverse=True):
                hours = int(seconds // 3600)  # Convert to int
                minutes = int((seconds % 3600) // 60)  # Convert to int
                secs = int(seconds % 60)  # Convert to int
                data.append([app, f"{hours:02d}h {minutes:02d}m {secs:02d}s"])

            table = Table(data, colWidths=[3*inch, 2*inch])
            table.setStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0969DA")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#E8F0FE")),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#3A4546")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#0969DA")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
            elements.append(Paragraph("Detailed Usage", styles['SubHeader']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(table)

        # Build the document with header and footer
        doc.build(elements, onFirstPage=lambda c, d: (header(c, d), footer(c, d)),
                  onLaterPages=lambda c, d: (header(c, d), footer(c, d)))

    def export_txt(self, filename, start_date, end_date):
        """Export a text report for the given date range."""
        usage_data = self._aggregate_usage(start_date, end_date)
        print(f"Debug: Aggregated usage data for text export: {usage_data}")
        with open(filename, 'w') as f:
            f.write(f"Time Tracking Report ({start_date} to {end_date})\n\n")
            f.write("Application\tTime Spent\n")
            total_seconds = sum(usage_data.values())
            hours = int(total_seconds // 3600)  # Convert to int
            minutes = int((total_seconds % 3600) // 60)  # Convert to int
            secs = int(total_seconds % 60)  # Convert to int
            f.write(f"\nTotal Tracked Time: {hours:02d}h {minutes:02d}m {secs:02d}s\n")
            for app, seconds in sorted(usage_data.items(), key=lambda x: x[1], reverse=True):
                hours = int(seconds // 3600)  # Convert to int
                minutes = int((seconds % 3600) // 60)  # Convert to int
                secs = int(seconds % 60)  # Convert to int
                f.write(f"{app}\t{hours:02d}h {minutes:02d}m {secs:02d}s\n")

    def _aggregate_usage(self, start_date, end_date):
        """Aggregate usage data for the given date range."""
        usage_data = {}
        current_date = start_date
        while current_date <= end_date:
            sessions = self.log_manager.read_sessions(current_date)
            print(f"Debug: Sessions for {current_date}: {sessions}")
            for session in sessions:
                app = session['app']
                duration = session['duration']
                usage_data[app] = usage_data.get(app, 0) + duration
            current_date = current_date + timedelta(days=1)
        return usage_data