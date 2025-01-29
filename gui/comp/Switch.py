from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient


class ToggleSwitch(QWidget):
    # Define a signal to emit the toggle state
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 30)  # Switch Container Size
        self.active = True  # Default: Chat Mode

        # Ball Inside the Switch
        self.ball = QLabel(self)
        self.ball.setGeometry(5, 5, 20, 20)
        self.ball.setStyleSheet(
            "border-radius: 10px; background-color: #FF6347;"
        )  # Initially Orangish

        # Label for Chat and Voice
        self.label = QLabel("Voice", self)
        self.label.setGeometry(40, 5, 35, 20)  # Initially on the left
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #909090; font-weight: bold;")
        self.animation = QPropertyAnimation(self.ball, b"geometry")
        self.animation.setDuration(200)  # Smooth slide animation

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()

    def toggle(self):
        if self.active:
            self.animation.setStartValue(QRect(55, 5, 20, 20))
            self.animation.setEndValue(QRect(5, 5, 20, 20))
            self.animation.setDuration(300)  # Slower animation
            self.label.setText("Voice")
            self.label.setGeometry(40, 5, 35, 20)  # Move text to left
            self.label.setStyleSheet("color: #909090; font-weight: bold;")
            self.ball.setStyleSheet(
                "border-radius: 10px; background-color: #FF6347;"
            )  # Ball turns light red
        else:
            self.animation.setStartValue(QRect(5, 5, 20, 20))
            self.animation.setEndValue(QRect(55, 5, 20, 20))
            self.animation.setDuration(300)  # Slower animation
            self.label.setText("Chat")
            self.label.setStyleSheet("color: #FF6347; font-weight: bold;")
            self.label.setGeometry(10, 5, 35, 20)  # Move text to right
            self.ball.setStyleSheet(
                "border-radius: 10px; background-color: #909090;"
            )  # Ball turns black

        self.active = not self.active
        self.animation.start()
        self.update()  # Refresh UI

        # Emit the toggle state
        self.toggled.emit(self.active)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create a gradient from left (gray) to right (black)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(155, 69, 0, 120))  # Reddish Start
        gradient.setColorAt(1, QColor(0, 40, 40, 220))  # Grayish End

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 80, 30, 15, 15)  # Rounded Container
