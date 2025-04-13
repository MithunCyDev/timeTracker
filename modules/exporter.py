from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime as dt

class ReportExporter:
    def __init__(self, log_manager):
        self.log_manager = log_manager

    def export_pdf(self, filename, start_date, end_date):
        """Export a PDF report for the given date range."""
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title = Paragraph(f"Time Tracking Report ({start_date} to {end_date})", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Fetch and aggregate data
        usage_data = self._aggregate_usage(start_date, end_date)

        # Table
        data = [["Application", "Time Spent"]]
        for app, seconds in sorted(usage_data.items(), key=lambda x: x[1], reverse=True):
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            data.append([app, f"{hours:02d}:{minutes:02d}:{secs:02d}"])

        table = Table(data)
        table.setStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        elements.append(table)

        doc.build(elements)

    def export_txt(self, filename, start_date, end_date):
        """Export a text report for the given date range."""
        usage_data = self._aggregate_usage(start_date, end_date)
        with open(filename, 'w') as f:
            f.write(f"Time Tracking Report ({start_date} to {end_date})\n\n")
            f.write("Application\tTime Spent\n")
            for app, seconds in sorted(usage_data.items(), key=lambda x: x[1], reverse=True):
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                f.write(f"{app}\t{hours:02d}:{minutes:02d}:{secs:02d}\n")

    def _aggregate_usage(self, start_date, end_date):
        """Aggregate usage data for the given date range."""
        usage_data = {}
        # Since start_date and end_date are typically the same for daily reports in gui.py,
        # we only need to fetch sessions for each date in the range
        current_date = start_date
        while current_date <= end_date:
            sessions = self.log_manager.read_sessions(current_date)
            for session in sessions:
                app = session['app']
                duration = session['duration']
                usage_data[app] = usage_data.get(app, 0) + duration
            # Increment date by one day
            current_date = (dt.combine(current_date, dt.min.time()) + 
                           dt.timedelta(days=1)).date()
        return usage_data