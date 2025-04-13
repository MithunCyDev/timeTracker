import sys
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QCalendarWidget, QTableWidget,
                            QTableWidgetItem, QPushButton, QFileDialog,
                            QMessageBox, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

try:
    import win32gui
    import win32process
except ImportError:
    pass  # Handle Linux/Mac later

LOG_FILE = os.path.expanduser("~/.time_tracker_logs.csv")

class ActivityTracker(QThread):
    activity_changed = pyqtSignal(str, str)  # timestamp, app_name

    def __init__(self):
        super().__init__()
        self.current_app = None
        self.last_log_time = None

    def get_active_window(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = win32process.GetModuleFileNameEx(win32process.OpenProcess(0x0400, False, pid), 0)
            return os.path.basename(process).split('.')[0]
        except:
            return "Unknown"

    def run(self):
        while True:
            current_app = self.get_active_window()
            if current_app != self.current_app:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.current_app is not None:
                    self.activity_changed.emit(timestamp, current_app)
                self.current_app = current_app
                self.last_log_time = time.time()
            time.sleep(1)

class LogManager:
    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def log_activity(self, timestamp, app_name):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, app_name])

    def get_entries(self, start_date=None, end_date=None):
        entries = []
        try:
            with open(LOG_FILE, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) != 2:
                        continue
                    entry_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    if start_date and entry_time.date() < start_date:
                        continue
                    if end_date and entry_time.date() > end_date:
                        continue
                    entries.append((entry_time, row[1]))
        except FileNotFoundError:
            pass
        return entries

class ReportGenerator:
    def __init__(self):
        self.log_manager = LogManager()

    def get_daily_summary(self, date):
        entries = self.log_manager.get_entries(date, date)
        return self._process_entries(entries)

    def get_weekly_summary(self, start_date):
        end_date = start_date + timedelta(days=6)
        entries = self.log_manager.get_entries(start_date, end_date)
        return self._process_entries(entries)

    def _process_entries(self, entries):
        if not entries:
            return {}

        usage_data = defaultdict(timedelta)
        prev_time, prev_app = entries[0]
        for entry_time, app_name in entries[1:]:
            duration = entry_time - prev_time
            usage_data[prev_app] += duration
            prev_time, prev_app = entry_time, app_name

        # Handle last entry
        if datetime.now().date() == prev_time.date():
            duration = datetime.now() - prev_time
        else:
            duration = timedelta(0)
        usage_data[prev_app] += duration

        return usage_data

class EmailDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setWindowTitle("Send Email")

        self.recipient = QLineEdit()
        self.sender = QLineEdit()
        self.password = QLineEdit(echoMode=QLineEdit.Password)
        self.smtp_server = QLineEdit()
        self.smtp_port = QLineEdit()
        self.send_btn = QPushButton("Send")

        form_layout = QFormLayout()
        form_layout.addRow("Recipient:", self.recipient)
        form_layout.addRow("Your Email:", self.sender)
        form_layout.addRow("Password:", self.password)
        form_layout.addRow("SMTP Server:", self.smtp_server)
        form_layout.addRow("SMTP Port:", self.smtp_port)

        layout.addLayout(form_layout)
        layout.addWidget(self.send_btn)
        self.setLayout(layout)
        
         # Add new controls
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Tracking")
        self.stop_btn = QPushButton("Stop Tracking")
        self.session_list = QListWidget()
        
        self.start_btn.clicked.connect(self.start_tracking)
        self.stop_btn.clicked.connect(self.stop_tracking)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        # Add to main layout
        layout.insertWidget(1, self.session_list)
        layout.insertLayout(1, control_layout)
        
        # Update styles
        self.session_list.setStyleSheet("""
            QListWidget { background-color: white; border-radius: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #ddd; }
        """)

class TimeTrackerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.report_generator = ReportGenerator()
        self.init_ui()
        self.init_tracker()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("Productivity Time Tracker")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        layout = QVBoxLayout()

        # Calendar and controls
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.update_display)

        # Summary Table
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Application", "Time Spent"])

        # Buttons
        btn_layout = QHBoxLayout()
        self.export_pdf_btn = QPushButton("Export PDF")
        self.export_txt_btn = QPushButton("Export Text")
        self.email_btn = QPushButton("Email Report")
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        self.export_txt_btn.clicked.connect(self.export_txt)
        self.email_btn.clicked.connect(self.send_email)

        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addWidget(self.export_txt_btn)
        btn_layout.addWidget(self.email_btn)

        layout.addWidget(self.calendar)
        layout.addWidget(self.summary_table)
        layout.addLayout(btn_layout)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QTableWidget { background-color: white; }
            QPushButton { 
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)

    def init_tracker(self):
        self.tracker = ActivityTracker()
        self.tracker.activity_changed.connect(self.handle_activity_change)
        self.tracker.start()

    def handle_activity_change(self, timestamp, app_name):
        LogManager().log_activity(timestamp, app_name)
        self.load_data()

    def load_data(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        self.daily_data = self.report_generator.get_daily_summary(selected_date)
        self.update_table()

    def update_table(self):
        self.summary_table.setRowCount(0)
        sorted_apps = sorted(self.daily_data.items(), 
                           key=lambda x: x[1], reverse=True)

        for row, (app, duration) in enumerate(sorted_apps):
            self.summary_table.insertRow(row)
            self.summary_table.setItem(row, 0, QTableWidgetItem(app))
            self.summary_table.setItem(row, 1, 
                QTableWidgetItem(str(duration).split('.')[0]))

    def update_display(self):
        self.load_data()

    def export_pdf(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", 
            f"TimeReport_{date}.pdf", "PDF Files (*.pdf)")

        if filename:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Title
            title = Paragraph(f"Time Tracking Report - {date}", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 12))

            # Table Data
            data = [["Application", "Time Spent"]]
            for app, duration in self.daily_data.items():
                data.append([app, str(duration).split('.')[0]])

            # Create table
            table = Table(data)
            table.setStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ])
            elements.append(table)
            doc.build(elements)

    def export_txt(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Text Report", 
            f"TimeReport_{date}.txt", "Text Files (*.txt)")

        if filename:
            with open(filename, 'w') as f:
                f.write(f"Time Tracking Report - {date}\n\n")
                f.write("Application\tTime Spent\n")
                for app, duration in self.daily_data.items():
                    f.write(f"{app}\t{str(duration).split('.')[0]}\n")

    def send_email(self):
        dialog = EmailDialog(self)
        dialog.send_btn.clicked.connect(lambda: self.handle_email(dialog))
        dialog.show()

    def handle_email(self, dialog):
        # Email sending logic
        try:
            msg = MIMEMultipart()
            msg['From'] = dialog.sender.text()
            msg['To'] = dialog.recipient.text()
            msg['Subject'] = "Time Tracking Report"

            body = "Attached is your time tracking report."
            msg.attach(MIMEText(body, 'plain'))

            # Create attachment
            date = self.calendar.selectedDate().toString("yyyy-MM-dd")
            report = MIMEApplication(self.generate_report_text())
            report.add_header('Content-Disposition', 'attachment', 
                            filename=f"report_{date}.txt")
            msg.attach(report)

            server = smtplib.SMTP(dialog.smtp_server.text(), 
                                 int(dialog.smtp_port.text()))
            server.starttls()
            server.login(dialog.sender.text(), dialog.password.text())
            server.send_message(msg)
            server.quit()
            QMessageBox.information(self, "Success", "Email sent successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")

    def generate_report_text(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        report = [f"Time Tracking Report - {date}\n\n"]
        for app, duration in self.daily_data.items():
            report.append(f"{app}: {str(duration).split('.')[0]}")
        return "\n".join(report)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimeTrackerGUI()
    window.show()
    sys.exit(app.exec_())