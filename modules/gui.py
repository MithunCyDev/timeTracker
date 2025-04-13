import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QListWidget, QDialog,
    QDialogButtonBox, QLabel, QLineEdit, QMessageBox, QFileDialog, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor
from datetime import datetime as dt
from modules.email_handler import EmailHandler
from modules.exporter import ReportExporter
from ui.components.chart_view import ChartView

class PermissionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Permission Required")
        self.setWindowIcon(QIcon("icons/app_icon.png"))
        layout = QVBoxLayout()
        message = QLabel(
            "This application needs permission to track your activity.\n"
            "All running applications will be monitored.\n\n"
            "No personal data or content will be collected. Only application names "
            "and usage durations are recorded."
        )
        message.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(message)
        layout.addWidget(buttons)
        self.setLayout(layout)

class EmailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Report via Email")
        self.setWindowIcon(QIcon("icons/app_icon.png"))
        layout = QVBoxLayout()
        self.recipient = QLineEdit()
        self.sender = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.smtp_server = QLineEdit("smtp.gmail.com")
        self.smtp_port = QLineEdit("587")
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Recipient:"))
        form_layout.addWidget(self.recipient)
        form_layout.addWidget(QLabel("Your Email:"))
        form_layout.addWidget(self.sender)
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.password)
        form_layout.addWidget(QLabel("SMTP Server:"))
        form_layout.addWidget(self.smtp_server)
        form_layout.addWidget(QLabel("SMTP Port:"))
        form_layout.addWidget(self.smtp_port)
        self.send_btn = QPushButton("Send")
        layout.addLayout(form_layout)
        layout.addWidget(self.send_btn)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self, tracker, logger):
        super().__init__()
        self.tracker = tracker
        self.logger = logger
        self.exporter = ReportExporter(logger)
        self.total_times = {}  # app: seconds
        self.total_elapsed_time = 0  # Total time since tracking started
        self.session_start_time = None
        self.init_ui()
        self.init_timers()
        self.setup_connections()
        
        # Initialize tracker with default settings
        self.tracker.set_tracked_apps()  # Track all apps by default
        self.tracker.start()  # Start the tracker thread (but not tracking yet)

    def init_ui(self):
        self.setWindowTitle("Productivity Tracker Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("icons/app_icon.png"))
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E1E; color: #E0E0E0; }
            QPushButton {
                background-color: #0288D1; color: #FFFFFF;
                border: none; padding: 8px; border-radius: 4px;
                font-size: 14px; min-width: 120px;
            }
            QPushButton:hover { background-color: #03A9F4; }
            QPushButton:disabled { background-color: #455A64; color: #B0BEC5; }
            QLabel { color: #E0E0E0; font-size: 14px; }
            QTableWidget {
                background-color: #2A2A2A; color: #E0E0E0;
                border: 1px solid #424242; gridline-color: #424242;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background-color: #0288D1; color: #FFFFFF;
                padding: 5px; border: none;
            }
            QListWidget {
                background-color: #2A2A2A; color: #E0E0E0;
                border: 1px solid #424242; border-radius: 4px;
            }
            QCalendarWidget { background-color: #2A2A2A; color: #E0E0E0; }
            QCalendarWidget QToolButton {
                color: #E0E0E0; background-color: #2A2A2A;
            }
            QCalendarWidget QWidget { alternate-background-color: #2A2A2A; }
            QStatusBar { background-color: #0288D1; color: #FFFFFF; }
        """)

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Left Panel
        left_panel = QVBoxLayout()
        
        # Create control layout first
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Tracking")
        self.stop_btn = QPushButton("Stop Tracking")
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # Create and configure labels
        self.current_app_label = QLabel("Currently Tracking: Code Editors, Browsers & Design Apps")
        self.current_app_label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        
        self.total_time_label = QLabel("Total Session Time: 00:00:00")
        self.total_time_label.setStyleSheet("font-size: 14px; color: #BBDEFB; font-weight: bold;")
        
        self.tracked_time_label = QLabel("Tracked Application Time: 00:00:00")
        self.tracked_time_label.setStyleSheet("font-size: 14px; color: #81C784; font-weight: bold;")

        # Add widgets to left panel in correct order
        left_panel.addWidget(self.current_app_label)
        left_panel.addWidget(self.total_time_label)
        left_panel.addWidget(self.tracked_time_label)
        left_panel.addLayout(control_layout)
        
        self.live_tracking_list = QListWidget()
        self.live_tracking_list.setMinimumWidth(300)
        left_panel.addWidget(QLabel("Live Tracking:"))
        left_panel.addWidget(self.live_tracking_list)

        # Right Panel
        right_panel = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.chart_view = ChartView()
        
        self.summary_table = QTableWidget(0, 2)
        self.summary_table.setHorizontalHeaderLabels(["Application", "Time Spent"])
        self.summary_table.setStyleSheet("selection-background-color: #0288D1;")
        self.summary_table.verticalHeader().hide()
        self.summary_table.setColumnWidth(0, 250)
        self.summary_table.setColumnWidth(1, 150)

        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Report")
        self.email_btn = QPushButton("Email Report")
        export_layout.addWidget(self.export_btn)
        export_layout.addWidget(self.email_btn)

        right_panel.addWidget(QLabel("Select Date:"))
        right_panel.addWidget(self.calendar)
        right_panel.addWidget(QLabel("Usage Distribution:"))
        right_panel.addWidget(self.chart_view)
        right_panel.addWidget(QLabel("Summary:"))
        right_panel.addWidget(self.summary_table)
        right_panel.addLayout(export_layout)

        # Combine panels
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        self.setWindowTitle("Productivity Tracker Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("icons/app_icon.png"))
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E1E; color: #E0E0E0; }
            QPushButton {
                background-color: #0288D1; color: #FFFFFF;
                border: none; padding: 8px; border-radius: 4px;
                font-size: 14px; min-width: 120px;
            }
            QPushButton:hover { background-color: #03A9F4; }
            QPushButton:disabled { background-color: #455A64; color: #B0BEC5; }
            QLabel { color: #E0E0E0; font-size: 14px; }
            QTableWidget {
                background-color: #2A2A2A; color: #E0E0E0;
                border: 1px solid #424242; gridline-color: #424242;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background-color: #0288D1; color: #FFFFFF;
                padding: 5px; border: none;
            }
            QListWidget {
                background-color: #2A2A2A; color: #E0E0E0;
                border: 1px solid #424242; border-radius: 4px;
            }
            QCalendarWidget { background-color: #2A2A2A; color: #E0E0E0; }
            QCalendarWidget QToolButton {
                color: #E0E0E0; background-color: #2A2A2A;
            }
            QCalendarWidget QWidget { alternate-background-color: #2A2A2A; }
            QStatusBar { background-color: #0288D1; color: #FFFFFF; }
        """)

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Left Panel
        left_panel = QVBoxLayout()
        self.current_app_label = QLabel("Currently Tracking: All Applications")
        self.current_app_label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        self.time_spent_label = QLabel("Time Spent: 00:00:00")
        self.time_spent_label.setStyleSheet("font-size: 16px; color: #BBDEFB;")
          # Add these new labels with different styling
        self.total_time_label = QLabel("Total Session Time: 00:00:00")
        self.total_time_label.setStyleSheet("font-size: 14px; color: #BBDEFB; font-weight: bold;")
        
        self.tracked_time_label = QLabel("Tracked Application Time: 00:00:00")
        self.tracked_time_label.setStyleSheet("font-size: 14px; color: #81C784; font-weight: bold;")
    

            # Add them to your layout before the control buttons
        left_panel.addWidget(self.current_app_label)
        left_panel.addWidget(self.total_time_label)
        left_panel.addWidget(self.tracked_time_label)
        left_panel.addLayout(control_layout)
        
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Tracking")
        self.stop_btn = QPushButton("Stop Tracking")
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        self.live_tracking_list = QListWidget()
        self.live_tracking_list.setMinimumWidth(300)
        left_panel.addWidget(self.current_app_label)
        left_panel.addWidget(self.time_spent_label)
        left_panel.addLayout(control_layout)
        left_panel.addWidget(QLabel("Live Tracking:"))
        left_panel.addWidget(self.live_tracking_list)

        # Right Panel
        right_panel = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.chart_view = ChartView()
        self.summary_table = QTableWidget(0, 2)
        self.summary_table.setHorizontalHeaderLabels(["Application", "Time Spent"])
        self.summary_table.setStyleSheet("selection-background-color: #0288D1;")
        self.summary_table.verticalHeader().hide()
        self.summary_table.setColumnWidth(0, 250)
        self.summary_table.setColumnWidth(1, 150)

        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Report")
        self.email_btn = QPushButton("Email Report")
        export_layout.addWidget(self.export_btn)
        export_layout.addWidget(self.email_btn)

        right_panel.addWidget(QLabel("Select Date:"))
        right_panel.addWidget(self.calendar)
        right_panel.addWidget(QLabel("Usage Distribution:"))
        right_panel.addWidget(self.chart_view)
        right_panel.addWidget(QLabel("Summary:"))
        right_panel.addWidget(self.summary_table)
        right_panel.addLayout(export_layout)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def setup_connections(self):
        """Connect all signals and slots"""
        # Connect tracker signals
        self.tracker.activity_changed.connect(self.on_activity_changed)
        self.tracker.tracking_update.connect(self.update_tracking_status)
        self.tracker.apps_updated.connect(self.on_apps_updated)
        
        # Connect UI buttons
        self.start_btn.clicked.connect(self.start_tracking)
        self.stop_btn.clicked.connect(self.stop_tracking)
        self.calendar.clicked.connect(self.update_report)
        self.export_btn.clicked.connect(self.export_report)
        self.email_btn.clicked.connect(self.show_email_dialog)


    def init_timers(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_total_time)

    def update_total_time(self):
        """Update the total elapsed time counter"""
        self.total_elapsed_time += 1
        self.time_spent_label.setText(f"Time Spent: {self.format_time(self.total_elapsed_time)}")

    def format_time(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        try:
            # Ensure we're working with a number
            total_seconds = float(seconds)
            # Round to nearest second
            total_seconds = round(total_seconds)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            secs = int(total_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except (ValueError, TypeError):
            return "00:00:00"

    def start_tracking(self):
        """Start the tracking session"""
        dialog = PermissionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Clear previous data
            self.live_tracking_list.clear()
            self.total_times.clear()
            self.total_elapsed_time = 0
            self.session_start_time = dt.now()
            
            # Start tracking
            self.tracker.toggle_tracking(True)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.timer.start(1000)
            
            # Update UI
            self.current_app_label.setText("Tracking: Development & Design Apps")
            self.status_bar.showMessage("Tracking started", 3000)
            
            # Log session start
            self.logger.log_activity(
                dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Session Started"
            )


    def stop_tracking(self):
        """Stop the tracking session"""
        self.tracker.toggle_tracking(False)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()
        
        # Update UI
        self.current_app_label.setText("Tracking: Inactive")
        self.status_bar.showMessage("Tracking stopped", 3000)
        
        # Log session end
        self.logger.end_current_session()
        self.logger.log_activity(
            dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Session Ended"
        )

    def on_activity_changed(self, timestamp, app_name, is_active):
        """Update live tracking list when app activity changes"""
        try:
            action = "▶" if is_active else "■"
            color = QColor("#4CAF50") if is_active else QColor("#F44336")
            
            item = QListWidgetItem(f"{timestamp} - {app_name} {action}")
            item.setForeground(color)
            
            # Set appropriate icon
            icon = self._get_app_icon(app_name.lower())
            if icon:
                item.setIcon(icon)
            
            # Add to top of list
            self.live_tracking_list.insertItem(0, item)
            
            # Limit to 20 items
            if self.live_tracking_list.count() > 20:
                self.live_tracking_list.takeItem(20)
                
            # Auto-scroll to top
            self.live_tracking_list.scrollToTop()
            
        except Exception as e:
            print(f"Error updating activity list: {e}")

    def on_apps_updated(self, app_durations):
        """Handle updated app duration data"""
        try:
            # Create a copy with float values converted to integers
            self.total_times = {app: float(duration) for app, duration in app_durations.items()}
            self.update_summary_table()
            
            # Calculate total time
            total_seconds = sum(self.total_times.values())
            self.time_spent_label.setText(f"Total Time: {self.format_time(total_seconds)}")
        except Exception as e:
            print(f"Error updating apps: {e}")

    def update_summary_table(self):
        self.summary_table.setRowCount(0)
        if not self.total_times:
            return
            
        total_tracked = sum(self.total_times.values())
        
        for app, seconds in sorted(self.total_times.items(), key=lambda x: x[1], reverse=True):
            row = self.summary_table.rowCount()
            self.summary_table.insertRow(row)
            
            # Calculate percentage
            percentage = (seconds / total_tracked) * 100 if total_tracked > 0 else 0
            
            # Add app name
            app_item = QTableWidgetItem(app)
            app_item.setIcon(self._get_app_icon(app.lower()))
            self.summary_table.setItem(row, 0, app_item)
            
            # Add formatted time and percentage
            time_str = f"{self.format_time(seconds)} ({percentage:.1f}%)"
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.summary_table.setItem(row, 1, time_item)
        
        self.chart_view.update_chart(self.total_times)

    def _get_app_icon(self, app_name):
        """Return appropriate icon for application"""
        icon_map = {
            # Browsers
            'chrome': 'browser',
            'firefox': 'browser',
            'edge': 'browser',
            'safari': 'browser',
            'opera': 'browser',
            'brave': 'browser',
            
            # Code Editors
            'code': 'vscode',
            'vscode': 'vscode',
            'visual studio': 'vs',
            'sublime': 'sublime',
            'atom': 'atom',
            
            # IDEs
            'android studio': 'android',
            'pycharm': 'pycharm',
            'intellij': 'intellij',
            
            # Design Tools
            'photoshop': 'photoshop',
            'illustrator': 'illustrator',
            'figma': 'figma',
            
            # Dev Tools
            'docker': 'docker',
            'postman': 'postman'
        }
        
        for key, icon in icon_map.items():
            if key in app_name.lower():
                return QIcon(f"icons/{icon}.png")
        return QIcon("icons/default.png")

    def update_report(self):
        """Load and display report for selected date"""
        selected_date = self.calendar.selectedDate().toPyDate()
        try:
            sessions = self.logger.read_sessions(selected_date)
            self.total_times = {session['app']: session['duration'] for session in sessions}
            self.update_summary_table()
            self.status_bar.showMessage(f"Showing report for {selected_date}", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"Error loading report: {str(e)}", 5000)
            print(f"Error loading report: {e}")

    def export_report(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        date_str = selected_date.strftime("%Y-%m-%d")
        options = "PDF Files (*.pdf);;Text Files (*.txt)"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Report", f"TimeReport_{date_str}", options
        )
        if filename:
            try:
                if filename.endswith('.pdf'):
                    self.exporter.export_pdf(filename, selected_date, selected_date)
                else:
                    self.exporter.export_txt(filename, selected_date, selected_date)
                QMessageBox.information(self, "Success", "Report exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export report: {str(e)}")

    def show_email_dialog(self):
        dialog = EmailDialog(self)
        dialog.send_btn.clicked.connect(lambda: self._send_email(
            dialog.recipient.text(),
            dialog.sender.text(),
            dialog.password.text(),
            dialog.smtp_server.text(),
            dialog.smtp_port.text()
        ))
        dialog.exec_()

    def _send_email(self, recipient, sender, password, server, port):
        try:
            handler = EmailHandler(server, int(port), sender, password)
            handler.send_report(recipient, self.total_times)
            QMessageBox.information(self, "Success", "Email sent successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")

    def update_tracking_status(self, is_tracking):
        """Update UI elements based on tracking state"""
        color = "#4CAF50" if is_tracking else "#F44336"
        self.status_bar.setStyleSheet(f"background-color: #0288D1; color: {color};")
        self.status_bar.showMessage("Tracking Active" if is_tracking else "Tracking Inactive")

    def closeEvent(self, event):
        """Clean up when window closes"""
        if self.tracker.tracking_enabled:
            self.stop_tracking()
        self.tracker.stop()  # Stop the tracker thread
        event.accept()