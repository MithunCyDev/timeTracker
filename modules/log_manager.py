import os
from datetime import datetime as dt
from collections import defaultdict
import threading

class LogManager:
    def __init__(self):
        self.log_file = "usage_data.txt"  # File in current working directory
        self._lock = threading.Lock()  # For thread-safe file operations
        self.current_app = None
        self.session_start_time = None
        self._initialize_log_file()

    def _initialize_log_file(self):
        """Initialize the log file if it doesn't exist."""
        with self._lock:
            log_dir = os.path.dirname(self.log_file)
            if log_dir:  # Only create directory if there is a directory path
                os.makedirs(log_dir, exist_ok=True)
            else:
                print(f"Debug: No directory path in log_file ({self.log_file}), skipping directory creation.")

            if not os.path.exists(self.log_file):
                print(f"Debug: Creating new log file at {self.log_file}")
                with open(self.log_file, "w") as f:
                    pass  # Just create an empty file
            else:
                print(f"Debug: Log file {self.log_file} already exists.")

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
                # Log "Session Started" if this is the start of a session
                if app_name == "Session Started":
                    with self._lock:
                        with open(self.log_file, "a") as f:
                            f.write(f"{timestamp},Session Started\n")
            else:
                self.current_app = None
                self.session_start_time = None
        except Exception as e:
            print(f"Error logging activity: {e}")

    def _write_session(self, app, start_time, end_time, duration):
        """Thread-safe session writing in plain-text format."""
        with self._lock:
            try:
                with open(self.log_file, "a") as f:
                    timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{timestamp},{app},{duration}\n")
                print(f"Debug: Wrote session - App: {app}, Duration: {duration}s")
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
        target_date_str = target_date.isoformat()
        print(f"Debug: Reading sessions for date {target_date_str} from file {self.log_file}")

        with self._lock:
            try:
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                print(f"Debug: Read {len(lines)} lines from {self.log_file}")
                print(f"Debug: File contents: {lines}")
            except FileNotFoundError:
                print(f"Debug: Log file {self.log_file} not found.")
                return []

            for line in lines:
                line = line.strip()
                if not line:
                    print(f"Debug: Skipping empty line")
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    print(f"Debug: Skipping malformed line: {line}")
                    continue

                # Parse timestamp
                try:
                    timestamp_str = parts[0]
                    timestamp = dt.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    line_date_str = timestamp.strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Debug: Invalid timestamp in line: {line}")
                    continue

                # Check if the line is for the target date
                if line_date_str != target_date_str:
                    print(f"Debug: Line date {line_date_str} does not match target date {target_date_str}, skipping")
                    continue

                # Parse the activity
                activity = parts[1]
                if activity in ["Session Started", "Session Ended"]:
                    print(f"Debug: Skipping session marker: {activity}")
                    continue

                # Parse app and duration
                if len(parts) >= 3:
                    app_name = activity
                    try:
                        duration = float(parts[2])
                        sessions[app_name] += duration
                        print(f"Debug: Processed session - App: {app_name}, Duration: {duration}s")
                    except ValueError:
                        print(f"Debug: Invalid duration in line: {line}")
                        continue
                else:
                    print(f"Debug: Incomplete data in line: {line}")

        # Convert defaultdict to list of dicts
        result = [{"app": app, "duration": duration} for app, duration in sessions.items()]
        print(f"Debug: Aggregated sessions: {result}")
        return result

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
            # Log "Session Ended"
            with self._lock:
                with open(self.log_file, "a") as f:
                    end_timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{end_timestamp},Session Ended\n")
            self.current_app = None
            self.session_start_time = None

    def clear_logs(self):
        """Clear all log data (use with caution)."""
        with self._lock:
            try:
                with open(self.log_file, "w") as f:
                    pass  # Just clear the file
                print(f"Debug: Cleared log file {self.log_file}")
            except Exception as e:
                print(f"Error clearing logs: {e}")