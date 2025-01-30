import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
)
import asyncio
import websockets
import json
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QFont, QPainter, QColor, QBrush, QLinearGradient
from comp.Switch import ToggleSwitch
import threading


class DesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Create a background event loop for async tasks
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_loop, daemon=True).start()
        self.setWindowTitle("Phoenix Body")
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - 1790) // 2
        y = (screen_geometry.height() + 398) // 2
        self.setGeometry(x, y, 450, 300)  # Original size

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
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)  # Add margins for better spacing

        # Top Bar Layout
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(0, 0, 0, 0)

        # "PHOENIX" Label at Top Left
        phoenix_label = QLabel("-PHOENIX-", self)
        phoenix_label.setFont(QFont("Arial", 18, QFont.Bold))
        font = phoenix_label.font()
        font.setItalic(True)
        phoenix_label.setFont(font)
        phoenix_label.setStyleSheet("color: #FF4500;")  # Fiery Red-Orange
        phoenix_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Switch at Top Right
        self.switch = ToggleSwitch()
        self.top_bar.addWidget(phoenix_label)
        self.top_bar.addStretch()  # Add stretch to push the switch to the right
        self.top_bar.addWidget(self.switch)

        # Add top bar to the main layout (always at the top)
        self.layout.addLayout(self.top_bar)

        # Connect switch toggled signal
        self.switch.toggled.connect(self.toggle_chat_input)

        # Chat Display Area (hidden by default)
        self.chat_display = QListWidget(self)
        self.chat_display.setStyleSheet(
            """
            QListWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #333333, stop:1 #000000);
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }
            """
        )
        self.chat_display.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )  # Hide scrollbar
        self.chat_display.hide()  # Hide by default

        # Chat Input Area (hidden by default)
        self.chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 10px;
                padding: 10px;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }
            """
        )
        self.chat_input.returnPressed.connect(self.send_message)

        # Clear Button
        self.clear_button = QPushButton("Clear", self)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #FF4500;
                color: white;
                border-radius: 10px;
                padding: 5px 10px;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF6347;
            }
            """
        )
        self.clear_button.clicked.connect(self.clear_chat)

        self.chat_input_layout.addWidget(self.chat_input)
        self.chat_input_layout.addWidget(self.clear_button)

        # Add chat display and input to the layout (below the top bar)
        self.layout.addWidget(self.chat_display)
        self.layout.addLayout(self.chat_input_layout)

        # Create a widget for the layout
        central_widget = QWidget(self)
        central_widget.setLayout(self.layout)
        central_widget.setGraphicsEffect(shadow)  # Apply shadow to main widget
        self.setCentralWidget(central_widget)

        # Variables for dragging
        self.dragging = False
        self.offset = QPoint()

    def start_loop(self):
        """Start asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def paintEvent(self, event):
        """Draw a modern glassy rounded background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(0, 40, 40, 220))  # Grayish End
        gradient.setColorAt(1, QColor(255, 69, 0, 70))  # Reddish Start
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

        # Ensure the window is properly updated
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press events to start dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move events to move the window."""
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events to stop dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def toggle_chat_input(self, checked):
        """Toggle the visibility of the chat input and display based on the switch state."""
        if not checked:  # Show chat interface only when switch is off (checked = False)
            self.chat_display.show()
            self.chat_input.show()
            self.clear_button.show()
        else:  # Hide chat interface when switch is on (checked = True)
            self.chat_display.hide()
            self.chat_input.hide()
            self.clear_button.hide()
        print("Toggle switched:", checked)

        # Force the layout to update
        self.layout.update()

    async def send_message_ws(self, user_prompt):
        """Send user prompt to WebSocket server and get AI response asynchronously."""
        async with websockets.connect("ws://127.0.0.1:8765") as websocket:
            await websocket.send(json.dumps({"user_prompt": user_prompt}))
            response = await websocket.recv()
            return json.loads(response).get("ai_prompt", "No response")

    def send_message(self):
        """Handles sending user message using WebSockets."""
        user_prompt = self.chat_input.text().strip()
        if not user_prompt:
            return

        # Display user input in the chat window (right-aligned with red background)
        user_message = QLabel(f"You: {user_prompt}")
        user_message.setStyleSheet(
            """
            QLabel {
                background-color: #FF0000;
                color: white;
                padding: 8px;
                border-radius: 15px;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }
            """
        )
        user_message.setAlignment(Qt.AlignRight)
        user_item = QListWidgetItem()
        user_item.setSizeHint(user_message.sizeHint())
        self.chat_display.addItem(user_item)
        self.chat_display.setItemWidget(user_item, user_message)

        self.chat_input.clear()

        # Fetch AI response
        async def fetch_response():
            ai_prompt = await self.send_message_ws(user_prompt)
            # Display AI response in the chat window (left-aligned with green background)
            ai_message = QLabel(f"Phoenix: {ai_prompt}")
            ai_message.setStyleSheet(
                """
                QLabel {
                    background-color: #00FF00;
                    color: black;
                    padding: 8px;
                    border-radius: 15px;
                    font-family: "Segoe UI", sans-serif;
                    font-size: 14px;
                }
                """
            )
            ai_message.setAlignment(Qt.AlignLeft)
            ai_item = QListWidgetItem()
            ai_item.setSizeHint(ai_message.sizeHint())
            self.chat_display.addItem(ai_item)
            self.chat_display.setItemWidget(ai_item, ai_message)

        # Run async function in the background
        asyncio.run_coroutine_threadsafe(fetch_response(), self.loop)

    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.clear()


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopWindow()
    window.show()
    sys.exit(app.exec_())
