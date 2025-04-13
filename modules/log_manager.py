import os
import csv
from datetime import datetime as dt
from collections import defaultdict
import threading

class LogManager:
    def __init__(self):
        self.log_file = os.path.expanduser("~/.time_tracker_logs.csv")
        self._lock = threading.Lock()  # For thread-safe file operations
        self.current_app = None
        self.session_start_time = None
        self._initialize_log_file()

    def _initialize_log_file(self):
        """Initialize the log file with headers if it doesn't exist."""
        with self._lock:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            if not os.path.exists(self.log_file):
                with open(self.log_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["date", "start_time", "end_time", "app", "duration"])

    def log_activity(self, timestamp, app_name):
        """
        Log an app switch, ending the previous session if necessary.
        Args:
            timestamp (str): Timestamp in "%Y-%m-%d %H:%M:%S" format
            app_name (str): Name of the application
        """
        try:
            parsed_time = dt.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            # End previous session if exists
            if self.current_app and self.session_start_time:
                duration = (parsed_time - self.session_start_time).total_seconds()
                if duration > 0:  # Only log if duration is positive
                    self._write_session(
                        app=self.current_app,
                        start_time=self.session_start_time,
                        end_time=parsed_time,
                        duration=int(duration)
                    )

            # Start new session if not "Session Ended"
            if app_name != "Session Ended":
                self.current_app = app_name
                self.session_start_time = parsed_time
            else:
                self.current_app = None
                self.session_start_time = None
        except Exception as e:
            print(f"Error logging activity: {e}")

    def _write_session(self, app, start_time, end_time, duration):
        """Thread-safe session writing."""
        with self._lock:
            try:
                with open(self.log_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        start_time.date().isoformat(),
                        start_time.strftime("%H:%M:%S"),
                        end_time.strftime("%H:%M:%S"),
                        app,
                        duration
                    ])
            except Exception as e:
                print(f"Error writing session: {e}")

    def read_sessions(self, target_date):
        """
        Read sessions for a specific date, aggregating durations by app.
        Args:
            target_date (date): Date to filter sessions
        Returns:
            list: List of dicts with app and duration
        """
        sessions = defaultdict(int)
        with self._lock:
            try:
                with open(self.log_file, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            if row["date"] == target_date.isoformat():
                                app = row["app"]
                                duration = float(row["duration"])
                                sessions[app] += duration
                        except (ValueError, KeyError) as e:
                            print(f"Skipping malformed log entry: {e}")
                            continue
            except FileNotFoundError:
                pass
        
        return [{"app": app, "duration": duration} for app, duration in sessions.items()]

    def end_current_session(self):
        """Cleanly end the current session if one exists."""
        if self.current_app and self.session_start_time:
            end_time = dt.now()
            duration = (end_time - self.session_start_time).total_seconds()
            if duration > 0:
                self._write_session(
                    app=self.current_app,
                    start_time=self.session_start_time,
                    end_time=end_time,
                    duration=int(duration)
                    )
            self.current_app = None
            self.session_start_time = None

    def clear_logs(self):
        """Clear all log data (use with caution)."""
        with self._lock:
            try:
                with open(self.log_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["date", "start_time", "end_time", "app", "duration"])
            except Exception as e:
                print(f"Error clearing logs: {e}")