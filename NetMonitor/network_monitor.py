#!/usr/bin/env python3
"""
Network Speed Monitor - Enhanced Draggable Edge Widget
A PyQt5-based desktop application with unified widget and panel dragging,
smart network monitoring, and beautiful black/gray theme.

Features:
- Unified dragging (widget + panel move together)
- Network monitoring only when expanded
- Outside click collapse
- Launch transition with 5-second display
- Beautiful black/gray theme with edge-specific rounded corners

Author: GitHub Copilot
Date: July 3, 2025
"""

import sys
import time
import psutil
import json
import os
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSystemTrayIcon,
    QMenu,
    QAction,
)
from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QRectF,
    pyqtSignal,
    QPoint,
    QSize,
    QEvent,
)
from PyQt5.QtGui import (
    QFont,
    QPalette,
    QColor,
    QIcon,
    QPainter,
    QBrush,
    QCursor,
    QPen,
    QPainterPath,
)


class NetworkMonitor:
    """Network monitoring utility using psutil"""

    def __init__(self):
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        self.last_time = time.time()
        self._initialize_network_stats()

    def _initialize_network_stats(self):
        """Initialize network statistics"""
        try:
            stats = psutil.net_io_counters()
            self.last_bytes_sent = stats.bytes_sent
            self.last_bytes_recv = stats.bytes_recv
        except Exception:
            self.last_bytes_sent = 0
            self.last_bytes_recv = 0

    def get_network_speed(self):
        """Get current network upload and download speeds"""
        try:
            current_time = time.time()
            stats = psutil.net_io_counters()

            time_diff = current_time - self.last_time
            if time_diff <= 0:
                return 0.0, 0.0

            bytes_sent_diff = stats.bytes_sent - self.last_bytes_sent
            bytes_recv_diff = stats.bytes_recv - self.last_bytes_recv

            # Convert to Mbps
            upload_speed = (bytes_sent_diff / time_diff) * 8 / (1024 * 1024)
            download_speed = (bytes_recv_diff / time_diff) * 8 / (1024 * 1024)

            self.last_bytes_sent = stats.bytes_sent
            self.last_bytes_recv = stats.bytes_recv
            self.last_time = current_time

            return upload_speed, download_speed

        except Exception as e:
            print(f"Error getting network speed: {e}")
            return 0.0, 0.0

    @staticmethod
    def format_speed(speed_mbps):
        """Format speed for display"""
        if speed_mbps >= 1.0:
            return f"{speed_mbps:.2f} Mbps"
        else:
            speed_kbps = speed_mbps * 1024
            return f"{speed_kbps:.1f} Kbps"


class GlobalClickFilter(QWidget):
    """Global event filter to detect clicks/touches anywhere on screen"""

    def __init__(self, network_widget):
        super().__init__()
        self.network_widget = network_widget

    def eventFilter(self, obj, event):
        """Filter all mouse press and touch events across the entire screen"""
        # Handle mouse clicks
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if self.network_widget.is_expanded:
                # Get the global position of the click
                click_pos = event.globalPos()

                # Get our widget's global geometry
                widget_rect = self.network_widget.geometry()

                # If the click is outside our widget area, collapse immediately
                if not widget_rect.contains(click_pos):
                    QTimer.singleShot(50, self.network_widget.collapse_widget)
                else:
                    # Click inside widget - reset the auto-collapse timer
                    self.network_widget.reset_auto_collapse_timer()

        # Handle touch events (for touchscreen support)
        elif event.type() == QEvent.TouchBegin:
            if self.network_widget.is_expanded:
                # For touch events, collapse on any touch outside the widget
                touch_points = event.touchPoints()
                if touch_points:
                    touch_pos = touch_points[0].screenPos().toPoint()
                    widget_rect = self.network_widget.geometry()

                    if not widget_rect.contains(touch_pos):
                        QTimer.singleShot(50, self.network_widget.collapse_widget)
                    else:
                        self.network_widget.reset_auto_collapse_timer()

        return False  # Always pass the event through


class UnifiedNetworkWidget(QWidget):
    """Unified widget that combines edge widget and expandable panel"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(
            Qt.WA_TranslucentBackground
        )  # Keep outer container transparent
        self.setAttribute(Qt.WA_AcceptTouchEvents)  # Enable touch events

        # Screen dimensions
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        # Widget dimensions (default and minimum sizes)
        self.widget_width = 12
        self.widget_height = 40
        self.panel_width = 280
        self.panel_height = 160
        self.min_panel_width = 220  # Increased to accommodate title + close button
        self.min_panel_height = 120
        self.max_panel_width = 500
        self.max_panel_height = 400

        # State variables
        self.is_expanded = False
        self.is_on_right = True
        self.dragging = False
        self.resizing = False
        self.drag_threshold = 5
        self.resize_threshold = 8
        self.mouse_press_position = QPoint()
        self.drag_start_position = QPoint()
        self.resize_start_position = QPoint()
        self.resize_start_size = QSize()

        # Network monitor (only created when needed)
        self.network_monitor = None

        # UI setup
        self.setup_ui()
        self.setup_styling()

        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_network_speeds)

        # Auto-collapse timer (10 seconds after hover)
        self.auto_collapse_timer = QTimer()
        self.auto_collapse_timer.setSingleShot(True)
        self.auto_collapse_timer.timeout.connect(self.collapse_widget)

        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.collapse_widget)

        # Hover delay timer (10 seconds after leaving hover)
        self.hover_delay_timer = QTimer()
        self.hover_delay_timer.setSingleShot(True)
        self.hover_delay_timer.timeout.connect(self.collapse_widget)

        self.launch_timer = QTimer()
        self.launch_timer.setSingleShot(True)
        self.launch_timer.timeout.connect(self.initial_collapse)

        # Position widget initially
        self.set_collapsed_state()
        self.load_position()  # Load saved position

        # Ensure styling is properly applied after setup
        self.update_inner_widget_style()

        # Update fonts after loading saved size
        self.update_title_font()
        self.update_label_fonts()

        # Enable mouse tracking for hover events
        self.setMouseTracking(True)

        # Show launch animation
        self.show_launch_animation()

    def setup_ui(self):
        """Setup the widget UI with container approach"""
        # Main container layout (transparent)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create inner widget (this will have the solid background)
        self.inner_widget = QWidget()
        self.inner_widget.setObjectName("inner_widget")
        container_layout.addWidget(self.inner_widget)
        self.setLayout(container_layout)

        # Inner widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.inner_widget.setLayout(layout)

        # Create panel content (initially hidden)
        self.panel_content = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(15, 12, 15, 15)
        panel_layout.setSpacing(8)

        # Title with toggle and close button
        title_container = QHBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(5)

        self.title_label = QLabel("Network Speed Monitor")
        self.update_title_font()
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(
            self.title_label.sizePolicy().Expanding,
            self.title_label.sizePolicy().Preferred,
        )

        # Auto-expand toggle button (radio-style)
        self.toggle_button = QLabel("●")
        self.toggle_button.setFixedSize(16, 16)
        self.toggle_button.setAlignment(Qt.AlignCenter)
        self.hover_expand_enabled = True  # Default: hover expand enabled
        self.update_toggle_button_style()
        self.toggle_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.toggle_button.mousePressEvent = self.toggle_hover_expand
        self.toggle_button.setToolTip("Toggle hover expand (●=on, ○=off)")

        # Close button
        self.close_button = QLabel("×")
        self.close_button.setFixedSize(18, 18)
        self.close_button.setAlignment(Qt.AlignCenter)
        self.close_button.setStyleSheet(
            """
            QLabel {
                color: #FF6B6B;
                background-color: transparent;
                border-radius: 9px;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid transparent;
            }
            QLabel:hover {
                background-color: rgba(255, 107, 107, 20);
                border: 1px solid rgba(255, 107, 107, 50);
            }
        """
        )
        self.close_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.close_button.mousePressEvent = self.close_button_clicked
        self.close_button.setToolTip("Close Network Monitor")

        title_container.addWidget(
            self.title_label, 1
        )  # Give title label stretch factor of 1
        title_container.addWidget(self.toggle_button, 0)  # Add toggle button
        title_container.addWidget(self.close_button, 0)  # Give close button no stretch
        panel_layout.addLayout(title_container)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        panel_layout.addWidget(separator)

        # Speed display
        speed_layout = QHBoxLayout()

        # Upload column
        upload_layout = QVBoxLayout()
        upload_layout.setSpacing(5)

        self.upload_label = QLabel("Upload")
        self.upload_label.setAlignment(Qt.AlignCenter)

        self.upload_speed_label = QLabel("0.00 Mbps")
        self.upload_speed_label.setAlignment(Qt.AlignCenter)

        upload_layout.addWidget(self.upload_label)
        upload_layout.addWidget(self.upload_speed_label)

        # Download column
        download_layout = QVBoxLayout()
        download_layout.setSpacing(5)

        self.download_label = QLabel("Download")
        self.download_label.setAlignment(Qt.AlignCenter)

        self.download_speed_label = QLabel("0.00 Mbps")
        self.download_speed_label.setAlignment(Qt.AlignCenter)

        download_layout.addWidget(self.download_label)
        download_layout.addWidget(self.download_speed_label)

        speed_layout.addLayout(upload_layout)
        speed_layout.addLayout(download_layout)
        panel_layout.addLayout(speed_layout)

        self.panel_content.setLayout(panel_layout)
        self.panel_content.hide()  # Initially hidden

        layout.addWidget(self.panel_content)

        # Update fonts after all labels are created
        self.update_label_fonts()

    def setup_styling(self):
        """Setup widget styling with black/gray theme"""
        # Set initial styling for inner widget
        self.update_inner_widget_style()

        # Style speed labels with colors
        self.upload_speed_label.setStyleSheet(
            "color: #4CAF50; background-color: transparent;"
        )
        self.download_speed_label.setStyleSheet(
            "color: #2196F3; background-color: transparent;"
        )
        self.title_label.setStyleSheet("color: #B0B0B0; background-color: transparent;")

        # Set cursor
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # Position settings file
        self.position_file = os.path.join(
            os.path.dirname(__file__), "widget_position.json"
        )

    def set_collapsed_state(self):
        """Set widget to collapsed state"""
        self.is_expanded = False
        self.setFixedSize(self.widget_width, self.widget_height)
        self.panel_content.hide()

        # Update styling for collapsed state
        self.update_inner_widget_style()

        # Stop network monitoring
        if self.update_timer.isActive():
            self.update_timer.stop()

    def set_expanded_state(self):
        """Set widget to expanded state"""
        self.is_expanded = True
        self.setFixedSize(self.panel_width, self.panel_height)
        self.panel_content.show()

        # Update styling for expanded state
        self.update_inner_widget_style()

        # Update fonts to match current size
        self.update_title_font()
        self.update_label_fonts()

        # Start network monitoring
        if not self.network_monitor:
            self.network_monitor = NetworkMonitor()
        self.update_timer.start(1000)  # Update every 1000ms (1 second) instead of 500ms

    def position_widget(self):
        """Position widget based on current state and edge"""
        if self.is_expanded:
            # Position expanded panel
            if self.is_on_right:
                x = self.screen_width - self.panel_width - 10
            else:
                x = 10

            # Center vertically or maintain current Y if possible
            current_y = (
                self.y()
                if hasattr(self, "y") and self.y() > 0
                else (self.screen_height - self.panel_height) // 2
            )
            y = max(0, min(current_y, self.screen_height - self.panel_height))
        else:
            # Position collapsed widget
            if self.is_on_right:
                x = self.screen_width - self.widget_width
            else:
                x = 0

            # Maintain Y position or center
            current_y = (
                self.y()
                if hasattr(self, "y") and self.y() > 0
                else (self.screen_height - self.widget_height) // 2
            )
            y = max(0, min(current_y, self.screen_height - self.widget_height))

        self.move(x, y)

    def save_position(self):
        """Save current widget position, size, state, and preferences to file"""
        try:
            position_data = {
                "x": self.x(),
                "y": self.y(),
                "width": self.panel_width,
                "height": self.panel_height,
                "is_on_right": self.is_on_right,
                "is_expanded": self.is_expanded,
                "hover_expand_enabled": self.hover_expand_enabled,
            }

            with open(self.position_file, "w") as f:
                json.dump(position_data, f)

        except Exception as e:
            print(f"Error saving position: {e}")

    def load_position(self):
        """Load widget position, size, state, and preferences from file"""
        try:
            if os.path.exists(self.position_file):
                with open(self.position_file, "r") as f:
                    position_data = json.load(f)

                # Restore edge preference
                self.is_on_right = position_data.get("is_on_right", True)

                # Restore hover expand preference
                self.hover_expand_enabled = position_data.get(
                    "hover_expand_enabled", True
                )

                # Restore panel size with bounds checking
                saved_width = position_data.get("width", self.panel_width)
                saved_height = position_data.get("height", self.panel_height)

                self.panel_width = max(
                    self.min_panel_width, min(saved_width, self.max_panel_width)
                )
                self.panel_height = max(
                    self.min_panel_height, min(saved_height, self.max_panel_height)
                )

                # Restore position with bounds checking
                saved_x = position_data.get("x", 0)
                saved_y = position_data.get("y", 0)

                # Ensure position is within current screen bounds
                if self.is_expanded:
                    max_x = self.screen_width - self.panel_width
                    max_y = self.screen_height - self.panel_height
                else:
                    max_x = self.screen_width - self.widget_width
                    max_y = self.screen_height - self.widget_height

                # Clamp to valid bounds
                x = max(0, min(saved_x, max_x))
                y = max(0, min(saved_y, max_y))

                self.move(x, y)

                # Update styling based on loaded state
                self.update_inner_widget_style()

                # Update toggle button style after loading preference
                if hasattr(self, "toggle_button"):
                    self.update_toggle_button_style()

            else:
                # No saved position, use default
                self.position_widget()

        except Exception as e:
            print(f"Error loading position: {e}")
            # Fall back to default positioning
            self.position_widget()

    def paintEvent(self, event):
        """Custom paint event - draw indicator dots for collapsed state"""
        if not self.is_expanded:
            # Draw dots with same color as border and 70% opacity
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Calculate dot positions
            dot_size = 2
            spacing = 6
            start_y = (self.height() - (3 * dot_size + 2 * spacing)) // 2

            # Use same color as border with 70% opacity (120, 120, 120, 180)
            dot_color = QColor(120, 120, 120, 180)  # 70% opacity

            for i in range(3):
                y = start_y + i * (dot_size + spacing)
                x = self.width() // 2 - dot_size // 2

                # Draw the dot with same color as border
                painter.setBrush(QBrush(dot_color))
                painter.setPen(QPen(dot_color, 1))
                painter.drawEllipse(x, y, dot_size, dot_size)

    def mousePressEvent(self, event):
        """Handle mouse press for dragging and resizing"""
        if event.button() == Qt.LeftButton:
            self.mouse_press_position = event.globalPos()
            self.drag_start_position = (
                event.globalPos() - self.frameGeometry().topLeft()
            )
            self.dragging = False
            self.resizing = False

            # Check if we're in a resize zone when expanded
            if self.is_expanded:
                local_pos = event.pos()
                resize_cursor = self.get_resize_cursor_zone(local_pos)
                if resize_cursor:
                    self.start_resize(self.mouse_press_position, resize_cursor)
                    return
                else:
                    # Reset auto-collapse timer on interaction
                    self.reset_auto_collapse_timer()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging, resizing, and cursor updates"""
        if event.buttons() == Qt.LeftButton:
            if self.resizing:
                # Handle resizing
                self.perform_resize(event.globalPos())
                return

            # Check if we should start dragging
            if not self.dragging and not self.resizing:
                move_distance = (
                    event.globalPos() - self.mouse_press_position
                ).manhattanLength()
                if move_distance > self.drag_threshold:
                    self.dragging = True
                    self.setCursor(QCursor(Qt.SizeAllCursor))
                    self.stop_auto_collapse_timer()  # Stop auto-collapse during drag

            # Drag the entire widget (collapsed or expanded)
            if self.dragging:
                new_pos = event.globalPos() - self.drag_start_position
                self.move(new_pos)
        else:
            # Update cursor based on mouse position when expanded
            if self.is_expanded and not self.dragging and not self.resizing:
                local_pos = event.pos()
                resize_cursor = self.get_resize_cursor_zone(local_pos)
                if resize_cursor:
                    self.setCursor(QCursor(resize_cursor))
                else:
                    self.setCursor(QCursor(Qt.PointingHandCursor))

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            if self.resizing:
                # Finish resizing
                self.finish_resize()
            elif self.dragging:
                # We were dragging - snap to edge and maintain state
                self.setCursor(QCursor(Qt.PointingHandCursor))
                self.snap_to_edge()
                self.dragging = False
                # No need to restart auto-collapse timer since we use hover
                # Position will be saved automatically by animate_to_edge
            else:
                # We weren't dragging or resizing - handle click behavior
                if self.is_expanded:
                    # Click to collapse when expanded (always works)
                    self.collapse_widget()
                elif not self.hover_expand_enabled:
                    # Click to expand when hover expand is disabled
                    self.expand_widget()

    def snap_to_edge(self):
        """Snap widget to nearest edge"""
        current_pos = self.pos()

        if self.is_expanded:
            center_x = current_pos.x() + self.panel_width // 2
        else:
            center_x = current_pos.x() + self.widget_width // 2

        # Determine which edge is closer
        old_is_on_right = self.is_on_right
        self.is_on_right = center_x > self.screen_width // 2

        # Update styling if edge changed
        if old_is_on_right != self.is_on_right:
            self.update_inner_widget_style()

        # Animate to proper position
        self.animate_to_edge()

    def animate_to_edge(self):
        """Animate widget to edge position"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        current_rect = self.geometry()

        if self.is_expanded:
            if self.is_on_right:
                target_x = self.screen_width - self.panel_width - 10
            else:
                target_x = 10
            target_width = self.panel_width
            target_height = self.panel_height
        else:
            if self.is_on_right:
                target_x = self.screen_width - self.widget_width
            else:
                target_x = 0
            target_width = self.widget_width
            target_height = self.widget_height

        # Keep Y within bounds
        target_y = max(0, min(current_rect.y(), self.screen_height - target_height))

        end_rect = QRect(target_x, target_y, target_width, target_height)

        self.animation.setStartValue(current_rect)
        self.animation.setEndValue(end_rect)
        self.animation.finished.connect(
            lambda: (
                self.repaint(),
                self.save_position(),
            )  # Save position after animation
        )
        self.animation.start()

    def toggle_expansion(self):
        """Toggle between collapsed and expanded states"""
        if self.is_expanded:
            self.collapse_widget()
        else:
            self.expand_widget()

    def expand_widget(self):
        """Expand widget to show network panel"""
        # Stop hide timer
        self.hide_timer.stop()

        # Set expanded state
        self.set_expanded_state()

        # Update responsive fonts
        self.update_title_font()
        self.update_label_fonts()

        # Position and animate
        self.animate_to_edge()

    def collapse_widget(self):
        """Collapse widget to edge"""
        # Stop all timers
        self.stop_auto_collapse_timer()
        self.hover_delay_timer.stop()

        # Set collapsed state
        self.set_collapsed_state()

        # Position and animate
        self.animate_to_edge()

    def update_network_speeds(self):
        """Update network speed display"""
        if not self.is_expanded or not self.network_monitor:
            return

        upload_speed, download_speed = self.network_monitor.get_network_speed()

        upload_text = self.network_monitor.format_speed(upload_speed)
        download_text = self.network_monitor.format_speed(download_speed)

        # Only update if the text has actually changed to prevent unnecessary repaints
        if self.upload_speed_label.text() != upload_text:
            self.upload_speed_label.setText(upload_text)
        if self.download_speed_label.text() != download_text:
            self.download_speed_label.setText(download_text)

    def show_launch_animation(self):
        """Show initial launch animation with sliding transition"""
        # Start in expanded state for 5 seconds
        self.set_expanded_state()

        # Ensure styling is applied immediately after setting expanded state
        self.update_inner_widget_style()

        # Update fonts to match the loaded size
        self.update_title_font()
        self.update_label_fonts()

        # Calculate final position
        if self.is_on_right:
            final_x = self.screen_width - self.panel_width - 10
        else:
            final_x = 10

        # Center vertically or maintain current Y if possible
        current_y = (
            self.y()
            if hasattr(self, "y") and self.y() > 0
            else (self.screen_height - self.panel_height) // 2
        )
        final_y = max(0, min(current_y, self.screen_height - self.panel_height))

        # Start position (off-screen)
        if self.is_on_right:
            start_x = self.screen_width  # Start from right edge, off-screen
        else:
            start_x = -self.panel_width  # Start from left edge, off-screen

        # Set initial position off-screen
        self.move(start_x, final_y)

        # Force style updates to take effect before showing
        self.repaint()
        QApplication.processEvents()

        self.show()

        # Create slide-in animation
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(600)  # 600ms slide duration
        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Set start and end rectangles for animation
        start_rect = QRect(start_x, final_y, self.panel_width, self.panel_height)
        end_rect = QRect(final_x, final_y, self.panel_width, self.panel_height)

        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(end_rect)

        # Start the slide animation
        self.slide_animation.start()

        # Set timer to collapse after 5 seconds (starts after animation begins)
        self.launch_timer.start(5000)

    def initial_collapse(self):
        """Initial collapse after launch animation"""
        self.collapse_widget()

    def closeEvent(self, event):
        """Handle widget close event"""
        self.save_position()
        super().closeEvent(event)

    def update_title_font(self):
        """Update title font size based on widget size"""
        if not hasattr(self, "title_label"):
            return  # Label not created yet

        # Calculate font size based on widget width, accounting for close button space
        available_width = (
            self.panel_width - 50
        )  # Reserve space for close button and margins
        base_size = max(8, min(14, int(available_width / 18)))
        title_font = QFont()
        title_font.setPointSize(base_size)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

    def update_label_fonts(self):
        """Update label fonts based on widget size"""
        # Check if all labels exist before updating
        if not all(
            hasattr(self, attr)
            for attr in [
                "upload_label",
                "download_label",
                "upload_speed_label",
                "download_speed_label",
            ]
        ):
            return  # Labels not created yet

        # Calculate font sizes based on widget dimensions
        label_size = max(7, min(12, int(self.panel_width / 25)))
        speed_size = max(10, min(18, int(self.panel_width / 18)))

        # Label font
        label_font = QFont()
        label_font.setPointSize(label_size)
        label_font.setBold(True)

        # Speed font
        speed_font = QFont()
        speed_font.setPointSize(speed_size)

        # Apply fonts
        self.upload_label.setFont(label_font)
        self.download_label.setFont(label_font)
        self.upload_speed_label.setFont(speed_font)
        self.download_speed_label.setFont(speed_font)

    def reset_auto_collapse_timer(self):
        """Reset the 10-second auto-collapse timer"""
        if self.is_expanded:
            self.auto_collapse_timer.stop()
            self.auto_collapse_timer.start(10000)  # 10 seconds

    def start_auto_collapse_timer(self):
        """Start the 10-second auto-collapse timer"""
        if self.is_expanded:
            self.auto_collapse_timer.start(10000)  # 10 seconds

    def stop_auto_collapse_timer(self):
        """Stop the auto-collapse timer"""
        self.auto_collapse_timer.stop()

    def get_resize_cursor_zone(self, pos):
        """Determine which resize zone the mouse is in with accurate cursor indicators"""
        if not self.is_expanded:
            return None

        margin = self.resize_threshold
        rect = self.rect()

        # Check corners first (for diagonal resize) - more precise detection
        if pos.x() <= margin and pos.y() <= margin:
            return Qt.SizeFDiagCursor  # Top-left (↖)
        elif pos.x() >= rect.width() - margin and pos.y() <= margin:
            return Qt.SizeBDiagCursor  # Top-right (↗)
        elif pos.x() <= margin and pos.y() >= rect.height() - margin:
            return Qt.SizeBDiagCursor  # Bottom-left (↙)
        elif pos.x() >= rect.width() - margin and pos.y() >= rect.height() - margin:
            return Qt.SizeFDiagCursor  # Bottom-right (↘)

        # Check edges - with clear directional indicators
        elif pos.x() <= margin:
            return Qt.SizeHorCursor  # Left edge (↔)
        elif pos.x() >= rect.width() - margin:
            return Qt.SizeHorCursor  # Right edge (↔)
        elif pos.y() <= margin:
            return Qt.SizeVerCursor  # Top edge (↕)
        elif pos.y() >= rect.height() - margin:
            return Qt.SizeVerCursor  # Bottom edge (↕)

        return None

    def start_resize(self, pos, cursor_type):
        """Start resizing the widget"""
        self.resizing = True
        self.resize_start_position = pos
        self.resize_start_size = self.size()
        self.resize_start_geometry = self.geometry()  # Store initial position too
        self.resize_cursor_type = cursor_type
        self.setCursor(QCursor(cursor_type))
        self.stop_auto_collapse_timer()  # Stop auto-collapse during resize

    def perform_resize(self, pos):
        """Perform the resize operation with proper directional behavior"""
        if not self.resizing:
            return

        delta = pos - self.resize_start_position
        new_width = self.resize_start_size.width()
        new_height = self.resize_start_size.height()
        new_x = self.resize_start_geometry.x()
        new_y = self.resize_start_geometry.y()

        # Apply resize based on cursor type with proper directional control
        if self.resize_cursor_type == Qt.SizeHorCursor:
            # Determine if this is left or right edge
            rect = self.rect()
            if (
                self.resize_start_position.x() - self.resize_start_geometry.x()
                <= self.resize_threshold
            ):
                # Left edge: dragging right decreases width, dragging left increases width
                new_width = self.resize_start_size.width() - delta.x()
                new_x = self.resize_start_geometry.x() + delta.x()
            else:
                # Right edge: dragging right increases width, dragging left decreases width
                new_width = self.resize_start_size.width() + delta.x()

        elif self.resize_cursor_type == Qt.SizeVerCursor:
            # Determine if this is top or bottom edge
            rect = self.rect()
            if (
                self.resize_start_position.y() - self.resize_start_geometry.y()
                <= self.resize_threshold
            ):
                # Top edge: dragging down decreases height, dragging up increases height
                new_height = self.resize_start_size.height() - delta.y()
                new_y = self.resize_start_geometry.y() + delta.y()
            else:
                # Bottom edge: dragging down increases height, dragging up decreases height
                new_height = self.resize_start_size.height() + delta.y()

        elif self.resize_cursor_type == Qt.SizeFDiagCursor:
            # Top-left or bottom-right corner
            rect = self.rect()
            start_local_x = (
                self.resize_start_position.x() - self.resize_start_geometry.x()
            )
            start_local_y = (
                self.resize_start_position.y() - self.resize_start_geometry.y()
            )

            if (
                start_local_x <= self.resize_threshold
                and start_local_y <= self.resize_threshold
            ):
                # Top-left corner
                new_width = self.resize_start_size.width() - delta.x()
                new_height = self.resize_start_size.height() - delta.y()
                new_x = self.resize_start_geometry.x() + delta.x()
                new_y = self.resize_start_geometry.y() + delta.y()
            else:
                # Bottom-right corner
                new_width = self.resize_start_size.width() + delta.x()
                new_height = self.resize_start_size.height() + delta.y()

        elif self.resize_cursor_type == Qt.SizeBDiagCursor:
            # Top-right or bottom-left corner
            rect = self.rect()
            start_local_x = (
                self.resize_start_position.x() - self.resize_start_geometry.x()
            )
            start_local_y = (
                self.resize_start_position.y() - self.resize_start_geometry.y()
            )

            if (
                start_local_x >= rect.width() - self.resize_threshold
                and start_local_y <= self.resize_threshold
            ):
                # Top-right corner
                new_width = self.resize_start_size.width() + delta.x()
                new_height = self.resize_start_size.height() - delta.y()
                new_y = self.resize_start_geometry.y() + delta.y()
            else:
                # Bottom-left corner
                new_width = self.resize_start_size.width() - delta.x()
                new_height = self.resize_start_size.height() + delta.y()
                new_x = self.resize_start_geometry.x() + delta.x()

        # Apply size constraints
        constrained_width = max(
            self.min_panel_width, min(new_width, self.max_panel_width)
        )
        constrained_height = max(
            self.min_panel_height, min(new_height, self.max_panel_height)
        )

        # Adjust position if size was constrained (for left/top edges)
        if new_width != constrained_width and new_x != self.resize_start_geometry.x():
            new_x = self.resize_start_geometry.x() + (
                self.resize_start_size.width() - constrained_width
            )
        if new_height != constrained_height and new_y != self.resize_start_geometry.y():
            new_y = self.resize_start_geometry.y() + (
                self.resize_start_size.height() - constrained_height
            )

        # Update panel dimensions
        self.panel_width = constrained_width
        self.panel_height = constrained_height

        # Update widget geometry (position and size)
        self.setGeometry(new_x, new_y, constrained_width, constrained_height)

        # Update font sizes for responsiveness
        self.update_title_font()
        self.update_label_fonts()

    def finish_resize(self):
        """Finish the resize operation"""
        if self.resizing:
            self.resizing = False
            self.setCursor(QCursor(Qt.PointingHandCursor))

            # Ensure widget is in fixed size mode with final dimensions
            self.setFixedSize(self.panel_width, self.panel_height)

            self.save_position()  # Save new size and position

    def enterEvent(self, event):
        """Handle mouse enter events to expand the widget"""
        # Stop any pending collapse timer
        self.hover_delay_timer.stop()

        # Only expand if hover expand is enabled, not already expanded, and not in middle of operations
        if (
            self.hover_expand_enabled
            and not self.is_expanded
            and not self.dragging
            and not self.resizing
        ):
            self.expand_widget()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave events to start collapse timer"""
        # Only auto-collapse if hover expand is enabled
        if (
            self.hover_expand_enabled
            and self.is_expanded
            and not self.dragging
            and not self.resizing
        ):
            self.hover_delay_timer.start(10000)  # 10 seconds delay
        super().leaveEvent(event)

    def close_button_clicked(self, event):
        """Handle close button click - terminate the application"""
        self.save_position()
        QApplication.instance().quit()

    def update_inner_widget_style(self):
        """Update inner widget style based on expanded state and edge position"""
        if self.is_expanded:
            # Expanded panel - edge-specific rounding with solid background
            if self.is_on_right:
                # Right edge: round left corners, square right corners
                border_radius = "border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
            else:
                # Left edge: round right corners, square left corners
                border_radius = "border-top-right-radius: 12px; border-bottom-right-radius: 12px; border-top-left-radius: 0px; border-bottom-left-radius: 0px;"

            # Apply solid background style for expanded state
            self.inner_widget.setStyleSheet(
                f"""
                QWidget#inner_widget {{
                    background-color: rgb(55, 55, 55);
                    border: 2px solid rgb(100, 100, 100);
                    {border_radius}
                }}
                QWidget#inner_widget:hover {{
                    background-color: rgb(70, 70, 70);
                }}
                QLabel {{
                    color: #C0C0C0;
                    background-color: transparent;
                }}
                QFrame {{
                    color: rgba(120, 120, 120, 150);
                }}
            """
            )
        else:
            # Collapsed widget - transparent background with border, dots and border same color
            self.inner_widget.setStyleSheet(
                """
                QWidget#inner_widget {
                    background-color: transparent;
                    border: 1px solid rgba(120, 120, 120, 180);
                    border-radius: 6px;
                }
                QLabel {
                    color: #C0C0C0;
                    background-color: transparent;
                }
                QFrame {
                    color: rgba(120, 120, 120, 150);
                }
            """
            )

        # Force immediate style update
        self.inner_widget.style().polish(self.inner_widget)
        self.inner_widget.update()

    def update_toggle_button_style(self):
        """Update toggle button style based on hover expand state"""
        if self.hover_expand_enabled:
            # Filled circle (●) when hover expand is enabled
            color = "#4CAF50"  # Green
            symbol = "●"
        else:
            # Empty circle (○) when hover expand is disabled
            color = "#757575"  # Gray
            symbol = "○"

        self.toggle_button.setText(symbol)
        self.toggle_button.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background-color: transparent;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid transparent;
            }}
            QLabel:hover {{
                background-color: rgba(117, 117, 117, 20);
                border: 1px solid rgba(117, 117, 117, 50);
            }}
        """
        )

    def toggle_hover_expand(self, event):
        """Toggle the hover expand functionality"""
        self.hover_expand_enabled = not self.hover_expand_enabled
        self.update_toggle_button_style()

        # Save the preference
        self.save_position()


class NetworkMonitorApp(QApplication):
    """Main application class"""

    def __init__(self, argv):
        super().__init__(argv)

        # Create unified widget
        self.network_widget = UnifiedNetworkWidget()

        # Create and install global click filter
        self.click_filter = GlobalClickFilter(self.network_widget)
        self.installEventFilter(self.click_filter)

        # Setup system tray (optional)
        self.setup_system_tray()

        # Show widget
        self.network_widget.show()

    def setup_system_tray(self):
        """Setup system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Monitor", self)
        show_action.triggered.connect(self.show_monitor)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Show message
        self.tray_icon.showMessage(
            "Network Monitor",
            "Network speed monitor is running. Hover to expand, use × button to close.",
            QSystemTrayIcon.Information,
            3000,
        )

    def show_monitor(self):
        """Show the network monitor"""
        if not self.network_widget.is_expanded:
            self.network_widget.expand_widget()

    def quit_application(self):
        """Quit application and save position"""
        self.network_widget.save_position()
        self.quit()


def network_main():
    """Main application entry point"""
    app = NetworkMonitorApp(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        sys.exit(0)


if __name__ == "__main__":
    network_main()
