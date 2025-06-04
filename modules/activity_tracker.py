import os
import time
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
import psutil

class ActivityTracker(QThread):
    activity_changed = pyqtSignal(str, str, bool)  # timestamp, app_name, is_active
    tracking_update = pyqtSignal(bool)
    apps_updated = pyqtSignal(dict)  # app_name: duration_in_seconds
    active_apps_updated = pyqtSignal(dict, dict)  # app_start_times, app_durations

    def __init__(self):
        super().__init__()
        self.tracking_enabled = False
        self.app_durations = {}  # Track total duration for each app
        self.app_start_times = {}  # Track when each app was last activated
        self.last_check = None
        self.running = True
        self.storage_file = "usage_data.txt"
        
        # Define the apps we want to track by default
        self.tracked_apps = {
            # Code Editors/IDEs
            'code', 'vscode', 'visual studio', 'android studio', 'studio', 'android-studio', 'pycharm',
            'sublime', 'atom', 'notepad++', 'intellij', 'eclipse', 'cursor',
            
            # Browsers
            'chrome', 'firefox', 'edge', 'safari', 'opera', 'brave',
            
            # Design Tools
            'photoshop', 'illustrator', 'figma', 'xd',
            
            # Development Tools
            'docker', 'postman', 'git', 'github desktop', 'wsl',
            
            # Terminals
            'terminal', 'cmd', 'powershell', 'windows terminal', 'iterm',
            
            # Databases
            'dbeaver', 'mysql', 'mongodb', 'postgresql'
        }

    def set_tracked_apps(self, apps=None):
        """Set specific apps to track, or None to use default tracked apps"""
        if apps is None:
            # Use default tracked apps
            return
        else:
            # Update with custom apps to track
            self.tracked_apps = {app.lower() for app in apps}

    def should_track_app(self, app_name):
        """Check if an app should be tracked based on our criteria"""
        app_lower = app_name.lower()
        
        # Skip system processes
        system_processes = {'system', 'idle', 'svchost', 'kernel', 'runtimebroker'}
        if app_lower in system_processes:
            return False
            
        # Check if this is one of our tracked apps
        for tracked_app in self.tracked_apps:
            if tracked_app in app_lower:
                return True
                
        return False

    def get_running_apps(self):
        """Get running applications, filtering for only tracked apps and those using more than 50MB memory"""
        apps = {}
        MEMORY_THRESHOLD = 50 * 1024 * 1024  # 50 MB in bytes
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
                try:
                    info = proc.info
                    # Get memory usage
                    memory_usage = info['memory_info'].rss  # Resident Set Size in bytes
                    # Try to get the executable name first
                    exe_name = os.path.basename(info['exe']).lower() if info.get('exe') else None
                    proc_name = info['name'].lower()
                    
                    # Use the most meaningful name available
                    app_name = exe_name or proc_name
                    app_name = os.path.splitext(app_name)[0]  # Remove extension
                    
                    print(f"Debug: Process found: {app_name} (PID: {info['pid']}, Memory: {memory_usage / (1024 * 1024):.2f} MB)")
                    
                    # Check if we should track this app based on name
                    if self.should_track_app(app_name):
                        # Check memory usage
                        if memory_usage > MEMORY_THRESHOLD:
                            # Standardize app names for consistency
                            standardized_name = self.standardize_app_name(app_name)
                            apps[standardized_name] = info['pid']
                            print(f"Debug: Tracked app: {standardized_name} (PID: {info['pid']}, Memory: {memory_usage / (1024 * 1024):.2f} MB)")
                        else:
                            print(f"Debug: Skipped app due to low memory: {app_name} (Memory: {memory_usage / (1024 * 1024):.2f} MB)")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"Debug: Skipped process due to {type(e).__name__}: {e}")
                    continue
                except Exception as e:
                    print(f"Debug: Unexpected error with process: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting running apps: {e}")
            
        if not apps:
            print("Debug: No tracked applications detected (above 50MB memory threshold)")
        else:
            print(f"Debug: Total tracked apps detected (above 50MB): {len(apps)}")
        return apps

    def standardize_app_name(self, app_name):
        """Convert similar app names to a standard format"""
        app_lower = app_name.lower()
        
        # Code Editors/IDEs
        if 'code' in app_lower or 'vscode' in app_lower:
            return 'VS Code'
        elif 'visual studio' in app_lower and 'code' not in app_lower:
            return 'Visual Studio'
        elif 'android studio' in app_lower or 'studio' in app_lower or 'android-studio' in app_lower:
            return 'Android Studio'
        elif 'pycharm' in app_lower:
            return 'PyCharm'
        elif 'sublime' in app_lower:
            return 'Sublime Text'
        elif 'intellij' in app_lower:
            return 'IntelliJ IDEA'
        elif 'cursor' in app_lower:
            return 'Cursor'
            
        # Browsers
        elif 'chrome' in app_lower:
            return 'Chrome'
        elif 'firefox' in app_lower:
            return 'Firefox'
        elif 'edge' in app_lower:
            return 'Edge'
        elif 'safari' in app_lower:
            return 'Safari'
        elif 'opera' in app_lower:
            return 'Opera'
        elif 'brave' in app_lower:
            return 'Brave'
            
        # Design Tools
        elif 'photoshop' in app_lower:
            return 'Photoshop'
        elif 'illustrator' in app_lower:
            return 'Illustrator'
        elif 'figma' in app_lower:
            return 'Figma'
        elif 'xd' in app_lower:
            return 'Adobe XD'
            
        # Development Tools
        elif 'docker' in app_lower:
            return 'Docker'
        elif 'postman' in app_lower:
            return 'Postman'
            
        # Default case - return original name but cleaned up
        return app_name.title()

    def store_app_usage(self, timestamp, app_name, duration):
        """Store the app usage in a text file when it closes"""
        try:
            with open(self.storage_file, 'a') as f:
                f.write(f"{timestamp},{app_name},{duration:.1f}\n")
            print(f"Debug: Stored usage for {app_name}: {duration:.1f}s at {timestamp}")
        except Exception as e:
            print(f"Error storing app usage: {e}")

    def read_app_usage(self, date_str):
        """Read stored app usage for a specific date, return aggregated durations"""
        aggregated_durations = {}
        try:
            if not os.path.exists(self.storage_file):
                print(f"Debug: Usage file {self.storage_file} does not exist")
                return aggregated_durations

            with open(self.storage_file, 'r') as f:
                for line in f:
                    try:
                        timestamp, app_name, duration = line.strip().split(',')
                        record_date = timestamp.split(' ')[0]  # Extract date part (e.g., "2025-04-14")
                        if record_date == date_str:
                            duration = float(duration)
                            aggregated_durations[app_name] = aggregated_durations.get(app_name, 0) + duration
                    except Exception as e:
                        print(f"Debug: Skipping invalid line in usage file: {line.strip()} (Error: {e})")
                        continue

            print(f"Debug: Read usage for {date_str}: {aggregated_durations}")
        except Exception as e:
            print(f"Error reading app usage: {e}")
        return aggregated_durations

    def run(self):
        """Main tracking loop"""
        while self.running:
            try:
                if self.tracking_enabled:
                    current_time = time.time()
                    if self.last_check is None:
                        self.last_check = current_time

                    # Get currently running apps
                    running_apps = self.get_running_apps()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # 1. Check for apps that have closed
                    for app in list(self.app_start_times.keys()):
                        if app not in running_apps:
                            # App has closed - record its duration
                            duration = current_time - self.app_start_times[app]
                            self.app_durations[app] = self.app_durations.get(app, 0) + duration
                            # Store the usage in the text file
                            self.store_app_usage(timestamp, app, duration)
                            del self.app_start_times[app]
                            self.activity_changed.emit(timestamp, app, False)
                            print(f"Debug: App closed: {app} (Duration: {duration:.1f}s)")

                    # 2. Check for new or continuing apps
                    for app in running_apps:
                        if app not in self.app_start_times:
                            # New app detected
                            self.app_start_times[app] = current_time
                            self.activity_changed.emit(timestamp, app, True)
                            print(f"Debug: New app detected: {app}")
                        else:
                            # App is still running - accumulate time
                            elapsed = current_time - self.last_check
                            self.app_durations[app] = self.app_durations.get(app, 0) + elapsed

                    # 3. Update the UI with current durations
                    self.apps_updated.emit(self.app_durations.copy())
                    self.active_apps_updated.emit(self.app_start_times.copy(), self.app_durations.copy())
                    print(f"Debug: Emitted active_apps_updated with {len(self.app_start_times)} active apps")
                    self.last_check = current_time
                    
                time.sleep(1)  # Reduce CPU usage
                
            except Exception as e:
                print(f"Error in tracking thread: {e}")
                time.sleep(5)  # Wait before retrying after error

    def toggle_tracking(self, enable):
        """Start or stop tracking"""
        self.tracking_enabled = enable
        if enable:
            print("Debug: Tracking started")
            self.last_check = time.time()  # Reset timing reference
        else:
            print("Debug: Tracking stopped")
            # Final update for all running apps
            current_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for app, start_time in self.app_start_times.items():
                duration = current_time - start_time
                self.app_durations[app] = self.app_durations.get(app, 0) + duration
                # Store the usage in the text file
                self.store_app_usage(timestamp, app, duration)
                self.activity_changed.emit(timestamp, app, False)
            self.app_start_times.clear()
            self.apps_updated.emit(self.app_durations.copy())
            self.active_apps_updated.emit({}, self.app_durations.copy())
        self.tracking_update.emit(enable)

    def stop(self):
        """Cleanly stop the tracking thread"""
        self.running = False
        self.toggle_tracking(False)
        self.wait()

    def get_current_stats(self):
        """Get current tracking statistics"""
        return {
            'durations': self.app_durations.copy(),
            'active_apps': self.app_start_times.copy(),
            'is_tracking': self.tracking_enabled
        }

    def reset_stats(self):
        """Reset all tracking statistics"""
        self.app_durations.clear()
        self.app_start_times.clear()
        self.apps_updated.emit({})