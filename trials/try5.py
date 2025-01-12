import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QColor

# Worker thread class
class WorkerThread(QThread):
    # Define a signal that will emit data to the main thread
    show_message_signal = pyqtSignal(str, str)

    def __init__(self, title, message):
        super().__init__()
        self.title = title
        self.message = message

    def run(self):
        # Emit the signal to show the message box
        self.show_message_signal.emit(self.title, self.message)

# Rounded message box class
class RoundedMessageBox(QDialog):
    def __init__(self, title, message):
        super().__init__()

        # Set up window attributes
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 150)
        self.init_ui(title, message)

    def init_ui(self, title, message):
        # Set up the layout with custom margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title label
        title_label = QLabel(title, self)
        title_label.setStyleSheet(
            "color: #f1c40f; font-size: 16px; font-weight: bold;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Message label
        message_label = QLabel(message, self)
        message_label.setStyleSheet("color: #ecf0f1; font-size: 14px;")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)

        # OK button
        ok_button = QPushButton("OK", self)
        ok_button.setStyleSheet(
            """
            QPushButton {
                background-color: #16a085;
                color: white;
                font-size: 12px;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1abc9c;
            }
            """
        )
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        ok_button.setFixedHeight(30)
        ok_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)

    def paintEvent(self, event):
        """Draw rounded corners and background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor("#2c3e50"))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

# Function to start the worker thread
def show_message_box(title, message):
    worker_thread = WorkerThread(title, message)
    worker_thread.start()
    return worker_thread

# Main function
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create the worker thread and connect its signal to show the message box
    worker_thread = show_message_box("Timer Alert", "Your timer is ringing!")
    worker_thread.show_message_signal.connect(lambda title, message: RoundedMessageBox(title, message).exec_())

    # Start the application event loop
    sys.exit(app.exec_())
