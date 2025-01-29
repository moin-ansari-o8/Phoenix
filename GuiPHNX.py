import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QBrush, QLinearGradient


class DesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Super Stylish GUI")
        self.setGeometry(65, 738, 450, 300)

        # Remove window frame & enable transparency
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Apply shadow effect for a floating look
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 150))  # Semi-transparent shadow

        # Create the main layout
        layout = QVBoxLayout()

        # Create a stylish label
        self.label = QLabel("Welcome to Stylish GUI", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 14, QFont.Bold))
        self.label.setStyleSheet("color: white;")
        layout.addWidget(self.label)

        # Create a modern styled button
        button = QPushButton("Click Me!")
        button.setFont(QFont("Arial", 12, QFont.Bold))
        button.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                           stop:0 #4CAF50, stop:1 #2E7D32);
                color: white;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #66BB6A;
                font-size: 16px;
            }
            QPushButton:pressed {
                background: #1B5E20;
            }
            """
        )
        button.clicked.connect(self.on_button_click)
        layout.addWidget(button)

        # Create a widget for the layout
        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        central_widget.setGraphicsEffect(shadow)  # Apply shadow to main widget
        self.setCentralWidget(central_widget)

    def on_button_click(self):
        """Change label text when button is clicked."""
        self.label.setText("Hello, You Clicked the Button!")
        self.label.setStyleSheet("color: #FFEB3B;")  # Change text color to yellow

    def paintEvent(self, event):
        """Draw a modern glassy rounded background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(30, 30, 30, 200))  # Dark glass effect
        gradient.setColorAt(1, QColor(60, 60, 60, 220))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopWindow()
    window.show()
    sys.exit(app.exec_())
