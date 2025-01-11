import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QBrush

class DesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop GUI")
        
        # Set window size and position
        self.setGeometry(100, 100, 200, 200)  # Set window size (300x200) and position (100, 100)
        
        # Set window flags (no taskbar and frameless window)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)  # Tool window (no taskbar)
        self.setAttribute(Qt.WA_TranslucentBackground)  # Make the background transparent
        
        # Create the main layout
        layout = QVBoxLayout()
        
        # Create a label with text
        self.label = QLabel("Hello from GUI", self)
        self.label.setAlignment(Qt.AlignCenter)  # Center the text
        self.label.setFont(QFont('Arial', 14, QFont.Bold))  # Set font style and size
        self.label.setStyleSheet("color: #333333;")  # Set label text color
        layout.addWidget(self.label)
        
        # Create a button and set its style
        button = QPushButton("Click Me!", self)
        button.setFont(QFont('Arial', 12))
        button.setStyleSheet("""
            QPushButton {
                background-color: blue;
                color: white;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button.clicked.connect(self.on_button_click)  # Connect the button click to the function
        layout.addWidget(button)
        
        # Create a widget for the layout and set it as the central widget
        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def on_button_click(self):
        """Change label text when button is clicked."""
        self.label.setText("Hello there!")
        self.label.setStyleSheet("color: #4CAF50;")  # Change text color to green

    def paintEvent(self, event):
        """Draw rounded corners and background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor("grey"))  # Background color (dark greyish blue)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 40)  # Draw rounded corners

# Example Usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopWindow()
    window.show()  # Show the window
    
    sys.exit(app.exec_())
