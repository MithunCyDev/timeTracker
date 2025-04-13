import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from modules.gui import MainWindow, PermissionDialog
from modules.activity_tracker import ActivityTracker
from modules.log_manager import LogManager

def main():
    app = QApplication(sys.argv)

    # Load stylesheet
    try:
        with open("assets/style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found. Proceeding with default styling.")

    # Check permissions
    permission_dialog = PermissionDialog()
    if permission_dialog.exec_() != QDialog.Accepted:
        QMessageBox.critical(None, "Permission Required",
                             "Application cannot run without permissions")
        sys.exit(1)

    # Initialize components
    logger = LogManager()
    tracker = ActivityTracker()
    window = MainWindow(tracker, logger)

    # Show main window
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()