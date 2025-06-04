import os
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QListWidget, QDialog,
    QDialogButtonBox, QLabel, QLineEdit, QMessageBox, QFileDialog, QStatusBar, QListWidgetItem
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
        self.active_apps = {}  # app: start_time
        self.app_durations = {}  # app: total duration
        self.init_ui()
        self.init_timers()
        self.setup_connections()
        self.tracker.set_tracked_apps()
        self.tracker.start()

    def init_ui(self):
        self.setWindowTitle("Productivity Tracker Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("icons/app_icon.png"))

        # Load stylesheet from file
        try:
            with open("assets/style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Left Panel
        left_panel = QVBoxLayout()
        self.current_app_label = QLabel("Currently Tracking: All Applications")
        self.current_app_label.setStyleSheet("font-size: 18px; color: #2DA44E; font-weight: bold; margin-bottom: 10px;")
        
        self.total_time_label = QLabel("Total Session Time: 00:00:00")
        self.total_time_label.setStyleSheet("font-size: 14px; color: #D3D7D9; font-weight: bold; margin-bottom: 5px;")
        
        self.tracked_time_label = QLabel("Tracked Application Time: 00:00:00")
        self.tracked_time_label.setStyleSheet("font-size: 14px; color: #2DA44E; font-weight: bold; margin-bottom: 15px;")

        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Tracking")
        self.stop_btn = QPushButton("Stop Tracking")
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        self.live_tracking_list = QListWidget()
        self.live_tracking_list.setMinimumWidth(300)
        left_panel.addWidget(self.current_app_label)
        left_panel.addWidget(self.total_time_label)
        left_panel.addWidget(self.tracked_time_label)
        left_panel.addLayout(control_layout)
        left_panel.addWidget(QLabel("Live Tracking:"))
        left_panel.addWidget(self.live_tracking_list)

        # Right Panel
        right_panel = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.chart_view = ChartView()
        self.chart_view.setMinimumHeight(300)  # Ensure enough space for the chart
        self.summary_table = QTableWidget(0, 2)
        self.summary_table.setHorizontalHeaderLabels(["Application", "Time Spent"])
        self.summary_table.setStyleSheet("selection-background-color: #0969DA;")
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
        self.start_btn.clicked.connect(self.start_tracking)
        self.stop_btn.clicked.connect(self.stop_tracking)
        self.calendar.clicked.connect(self.update_report)
        self.export_btn.clicked.connect(self.export_report)
        self.email_btn.clicked.connect(self.show_email_dialog)
        self.tracker.activity_changed.connect(self.on_activity_changed)
        self.tracker.tracking_update.connect(self.update_tracking_status)
        self.tracker.apps_updated.connect(self.on_apps_updated)
        self.tracker.active_apps_updated.connect(self.on_active_apps_updated)

    def init_timers(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_total_time)

    def start_tracking(self):
        dialog = PermissionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.live_tracking_list.clear()
            self.total_times.clear()
            self.active_apps.clear()
            self.app_durations.clear()
            self.total_elapsed_time = 0
            self.session_start_time = dt.now()
            self.tracker.toggle_tracking(True)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.timer.start(1000)
            self.current_app_label.setText("Tracking: All Applications")
            self.status_bar.showMessage("Tracking started", 3000)
            self.logger.log_activity(
                dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Session Started"
            )
        else:
            self.status_bar.showMessage("Permission Denied - Tracking Not Started", 3000)
            print("Debug: Permission denied")

    def stop_tracking(self):
        self.tracker.toggle_tracking(False)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()
        self.current_app_label.setText("Tracking: Inactive")
        self.live_tracking_list.clear()
        self.status_bar.showMessage("Tracking stopped", 3000)
        self.logger.end_current_session()
        self.logger.log_activity(
            dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Session Ended"
        )

    def on_activity_changed(self, timestamp, app_name, is_active):
        try:
            print(f"Debug: Activity changed - {timestamp}, {app_name}, is_active: {is_active}")
            if is_active:
                self.logger.log_activity(timestamp, app_name)
        except Exception as e:
            print(f"Error in on_activity_changed: {e}")

    def on_active_apps_updated(self, app_start_times, app_durations):
        try:
            print(f"Debug: Active apps updated - Active: {app_start_times}, Durations: {app_durations}")
            self.active_apps = app_start_times.copy()
            self.app_durations = app_durations.copy()
            self.update_live_tracking_list()
            # Update chart with current session data
            combined_usage = self.tracker.read_app_usage(dt.now().strftime("%Y-%m-%d")).copy()
            for app, duration in self.app_durations.items():
                combined_usage[app] = combined_usage.get(app, 0) + duration
            self.total_times = combined_usage
            self.chart_view.update_chart(self.total_times)
        except Exception as e:
            print(f"Error updating live tracking list: {e}")

    def update_live_tracking_list(self):
        self.live_tracking_list.clear()
        if not self.active_apps:
            self.live_tracking_list.addItem("No applications currently active")
            return

        current_time = time.time()
        app_times = {}
        for app, start_time in self.active_apps.items():
            live_duration = current_time - start_time
            total_duration = self.app_durations.get(app, 0)
            app_times[app] = total_duration

        # Sort apps by total duration (most used first)
        sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)

        for app, total_duration in sorted_apps:
            start_time = self.active_apps[app]
            live_duration = current_time - start_time
            formatted_time = self.format_time(live_duration)
            item = QListWidgetItem(f"{app}: {formatted_time}")
            item.setIcon(self._get_app_icon(app.lower()))
            item.setForeground(QColor("#2DA44E"))
            self.live_tracking_list.addItem(item)

    def on_apps_updated(self, app_durations):
        try:
            print(f"Debug: Apps updated - {app_durations}")
            self.total_times = {app: float(duration) for app, duration in app_durations.items()}
            total_tracked = sum(self.total_times.values())
            self.tracked_time_label.setText(f"Tracked Application Time: {self.format_time(total_tracked)}")
            self.update_summary_table()
            if not self.total_times:
                print("Debug: No apps detected for chart update")
                self.chart_view.update_chart({})
        except Exception as e:
            print(f"Error updating apps: {e}")

    def update_total_time(self):
        self.total_elapsed_time += 1
        self.total_time_label.setText(f"Total Session Time: {self.format_time(self.total_elapsed_time)}")
        self.update_live_tracking_list()  # Update live tracking list every second
        print(f"Debug: Total time updated - {self.total_elapsed_time} seconds")

    def format_time(self, seconds):
        try:
            total_seconds = float(seconds)
            total_seconds = round(total_seconds)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            secs = int(total_seconds % 60)
            if hours > 0:
                return f"{hours} hr {minutes} min"
            elif minutes > 0:
                return f"{minutes} min {secs} sec"
            else:
                return f"{secs} sec"
        except (ValueError, TypeError):
            return "0 sec"

    def update_summary_table(self):
        self.summary_table.setRowCount(0)
        if not self.total_times:
            return
        total_tracked = sum(self.total_times.values())
        for app, seconds in sorted(self.total_times.items(), key=lambda x: x[1], reverse=True):
            row = self.summary_table.rowCount()
            self.summary_table.insertRow(row)
            percentage = (seconds / total_tracked) * 100 if total_tracked > 0 else 0
            app_item = QTableWidgetItem(app)
            app_item.setIcon(self._get_app_icon(app.lower()))
            self.summary_table.setItem(row, 0, app_item)
            time_str = f"{self.format_time(seconds)} ({percentage:.1f}%)"
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.summary_table.setItem(row, 1, time_item)

    def _get_app_icon(self, app_name):
        icon_map = {
            'chrome': 'browser',
            'firefox': 'browser',
            'edge': 'browser',
            'safari': 'browser',
            'opera': 'browser',
            'brave': 'browser',
            'code': 'vscode',
            'vscode': 'vscode',
            'visual studio': 'vs',
            'sublime': 'sublime',
            'atom': 'atom',
            'android studio': 'android',
            'pycharm': 'pycharm',
            'intellij': 'intellij',
            'photoshop': 'photoshop',
            'illustrator': 'illustrator',
            'figma': 'figma',
            'docker': 'docker',
            'postman': 'postman'
        }
        for key, icon in icon_map.items():
            if key in app_name.lower():
                return QIcon(f"icons/{icon}.png")
        return QIcon("icons/default.png")

    def update_report(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        date_str = selected_date.strftime("%Y-%m-%d")
        try:
            # Read stored usage data for the selected date
            stored_usage = self.tracker.read_app_usage(date_str)
            # Combine with in-memory data (if tracking is active)
            current_usage = self.tracker.get_current_stats()['durations']
            combined_usage = stored_usage.copy()
            for app, duration in current_usage.items():
                combined_usage[app] = combined_usage.get(app, 0) + duration

            self.total_times = combined_usage
            print(f"Debug: Updating chart with data for {date_str}: {self.total_times}")
            self.update_summary_table()
            self.chart_view.update_chart(self.total_times)
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
        color = "#2DA44E" if is_tracking else "#F44336"
        self.status_bar.setStyleSheet(f"background-color: #0969DA; color: {color};")
        self.status_bar.showMessage("Tracking Active" if is_tracking else "Tracking Inactive")

    def closeEvent(self, event):
        if self.tracker.tracking_enabled:
            self.stop_tracking()
        self.tracker.quit()
        self.tracker.wait()
        event.accept()