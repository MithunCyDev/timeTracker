from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtCore import Qt

class ChartView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        
        self.label = QLabel("Time Distribution by Application")
        self.label.setAlignment(Qt.AlignCenter)
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        
        layout.addWidget(self.label)
        layout.addWidget(self.text_display)
        self.setLayout(layout)

    def update_chart(self, app_data):
        """Update the pie chart with new application data"""
        try:
            self.figure.clear()
            
            if not app_data:
                # Handle empty data case
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, 'No data available', 
                    ha='center', va='center')
                self.canvas.draw()
                return
                
            # Prepare data
            total = sum(app_data.values())
            labels = []
            sizes = []
            text = "Application Usage:\n\n"
            
            for app, seconds in sorted(app_data.items(), key=lambda x: x[1], reverse=True):
                # Convert seconds to hours, minutes, seconds
                total_seconds = float(seconds)
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                secs = int(total_seconds % 60)
                percentage = (total_seconds / total) * 100 if total > 0 else 0
                
                labels.append(app)
                sizes.append(total_seconds)
                text += f"{app}: {hours:02d}:{minutes:02d}:{secs:02d} ({percentage:.1f}%)\n"
            
            # Create pie chart
            ax = self.figure.add_subplot(111)
            ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures pie is circular
            
            # Update the text display
            self.text_display.setPlainText(text)
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating chart: {e}")