from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint

class ChartView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}  # {app_name: duration_in_seconds}
        self.bar_rects = []  # Initialize bar_rects to avoid AttributeError
        self.setMouseTracking(True)  # Enable mouse tracking for tooltips
        self.hovered_bar = None
        self.setMinimumHeight(300)

    def update_chart(self, data):
        """Update the chart with new data"""
        self.data = data
        print(f"Debug: ChartView received data: {self.data}")
        self.hovered_bar = None
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Define colors from the app's theme
        background_color = QColor("#2A3536")
        bar_color = QColor("#0969DA")
        highlight_color = QColor("#2DA44E")
        text_color = QColor("#D3D7D9")
        border_color = QColor("#3A4546")

        # Fill background
        painter.fillRect(self.rect(), background_color)

        # Reset bar_rects
        self.bar_rects = []

        if not self.data:
            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "No data to display")
            return

        # Chart dimensions
        width = int(self.width())
        height = int(self.height())
        margin = 40  # Margin for labels and borders
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        # Calculate bar width and spacing
        num_bars = len(self.data)
        if num_bars == 0:
            return
        bar_width = chart_width // num_bars - 10  # 10px spacing between bars
        if bar_width < 20:
            bar_width = 20  # Minimum bar width
        bar_spacing = 10

        # Find the maximum duration for scaling
        max_duration = max(self.data.values(), default=1)
        if max_duration == 0:
            max_duration = 1  # Avoid division by zero

        # Draw bars
        painter.setFont(QFont("Segoe UI", 10))
        x = margin
        bar_index = 0

        for app, duration in self.data.items():
            # Calculate bar height
            bar_height = (duration / max_duration) * (chart_height - 20)  # 20px for label
            if bar_height < 5:
                bar_height = 5  # Minimum bar height for visibility
            bar_height = int(bar_height)  # Convert to integer

            # Bar position
            y = height - margin - bar_height
            y = int(y)  # Convert to integer
            bar_rect = QRect(x, y, bar_width, bar_height)
            self.bar_rects.append((bar_rect, app, duration))

            # Determine bar color (highlight if hovered)
            if self.hovered_bar == bar_index:
                painter.setBrush(highlight_color)
            else:
                painter.setBrush(bar_color)

            # Draw bar
            painter.setPen(border_color)
            painter.drawRect(bar_rect)

            # Draw app name (rotated 45 degrees for readability)
            painter.save()
            painter.translate(x + bar_width // 2, height - margin + 10)
            painter.rotate(-45)
            painter.setPen(text_color)
            painter.drawText(0, 0, app[:15])  # Truncate long names
            painter.restore()

            # Draw duration label above bar
            formatted_time = self.format_time(duration)
            painter.setPen(text_color)
            painter.drawText(x, y - 10, f"{formatted_time}")

            x += bar_width + bar_spacing
            bar_index += 1

        # Draw Y-axis labels (time)
        painter.setPen(text_color)
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(0, 5):  # 5 steps on Y-axis
            fraction = i / 4
            y = height - margin - fraction * chart_height
            y = int(y)  # Convert to integer
            duration = fraction * max_duration
            painter.drawText(margin - 30, y + 5, self.format_time(duration))

    def format_time(self, seconds):
        """Format duration in seconds to a readable string"""
        total_seconds = round(float(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def mouseMoveEvent(self, event):
        """Handle mouse movement to show tooltips"""
        pos = event.pos()
        self.hovered_bar = None
        for index, (rect, app, duration) in enumerate(self.bar_rects):
            if rect.contains(pos):
                self.hovered_bar = index
                formatted_time = self.format_time(duration)
                self.setToolTip(f"{app}: {formatted_time}")
                break
        else:
            self.setToolTip("")
        self.update()  # Repaint to show highlight

    def resizeEvent(self, event):
        """Handle widget resize"""
        super().resizeEvent(event)
        self.update()