from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout
from PyQt5.QtCore import Qt


class ChatInput(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a layout for the chat input
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Create an input box with a placeholder
        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("Enter Your Command")
        self.input_box.setStyleSheet(
            """
            QLineEdit {
                border: 2px solid #FF4500;
                border-radius: 10px;
                padding: 5px;
                background-color: rgba(255, 255, 255, 150);
                color: #000000;
            }
            """
        )

        # Add the input box to the layout
        layout.addWidget(self.input_box)
        self.setLayout(layout)
