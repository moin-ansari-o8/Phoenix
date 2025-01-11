from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont

class RoundedMessageBox(QDialog):
    def __init__(self, title, message):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 150)
        self.init_ui(title, message)

    def init_ui(self, title, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title Label
        title_label = QLabel(title, self)
        title_label.setStyleSheet("color: #f1c40f; font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Message Label
        message_label = QLabel(message, self)
        message_label.setStyleSheet("color: #ecf0f1; font-size: 14px;")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)

        # OK Button
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

# Example Usage
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    message_box = RoundedMessageBox("Custom Title", "This is a custom message box with rounded corners!")
    message_box.exec_()

    sys.exit(app.exec_())
