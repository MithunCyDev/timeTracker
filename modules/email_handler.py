import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import tempfile

class EmailHandler:
    def __init__(self, smtp_server, smtp_port, sender_email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password

    def generate_pdf_report(self, usage_data):
        # Create a temporary PDF file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Add title
        title = Paragraph("Time Tracking Report", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Create table data
        data = [["Application", "Time Spent"]]
        for app, seconds in usage_data.items():
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            data.append([app, f"{hours:02d}:{minutes:02d}:{secs:02d}"])

        # Style the table
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

        # Build PDF
        doc.build(elements)
        return temp_file.name

    def send_report(self, recipient, usage_data):
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient
        msg['Subject'] = "Productivity Tracker Pro - Activity Report"

        # Create text body
        body = "Dear User,\n\nHere is your time tracking report:\n\n"
        for app, seconds in usage_data.items():
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            body += f"{app}: {hours:02d}:{minutes:02d}:{secs:02d}\n"
        body += "\nA detailed PDF report is attached.\n\nBest regards,\nProductivity Tracker Pro"
        msg.attach(MIMEText(body, 'plain'))

        # Generate and attach PDF
        pdf_path = self.generate_pdf_report(usage_data)
        try:
            with open(pdf_path, 'rb') as f:
                pdf = MIMEApplication(f.read(), _subtype="pdf")
                pdf.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename="TimeTrackingReport.pdf"
                )
                msg.attach(pdf)
        finally:
            os.unlink(pdf_path)  # Clean up temporary file

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.password)
                server.send_message(msg)
        except smtplib.SMTPAuthenticationError:
            raise Exception("Authentication failed. Please check your email and password.")
        except smtplib.SMTPConnectError:
            raise Exception("Failed to connect to the SMTP server. Please check server settings.")
        except Exception as e:
            raise Exception(f"An error occurred while sending the email: {str(e)}")