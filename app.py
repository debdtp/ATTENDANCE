import os
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem, 
                             QStackedWidget, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

import database
import config
from dashboard import DashboardWidget
from register import RegisterWidget
from recognize import RecognizeWidget
from attendance_history import HistoryWidget
from student_management import StudentManagementWidget
from settings import SettingsWidget

# Premium Dark Mode QSS Stylesheet
QSS_STYLESHEET = """
QMainWindow {
    background-color: #0B0F19; /* Dark Navy Backdrop */
}

/* Sidebar Styling */
#sidebarFrame {
    background-color: #0F172A; /* Slate Navy */
    border-right: 1px solid #1E293B;
}

#sidebarTitle {
    color: #818CF8; /* Vibrant Indigo */
    font-size: 18px;
    font-weight: bold;
    padding-bottom: 2px;
}

#sidebarSubtitle {
    color: #94A3B8;
    font-size: 10px;
    font-weight: 500;
}

/* Navigation List */
QListWidget {
    background-color: transparent;
    border: none;
    outline: 0;
}

QListWidget::item {
    color: #94A3B8;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 500;
    padding: 12px 15px;
    border-radius: 8px;
    margin-bottom: 5px;
}

QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.03);
    color: #F8FAFC;
}

QListWidget::item:selected {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
    background-color: #4F46E5; /* Fallback */
    color: #FFFFFF;
    font-weight: bold;
}

/* Page Widgets General Styling */
QGroupBox {
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    font-family: 'Outfit', sans-serif;
    font-weight: bold;
    color: #F8FAFC;
    font-size: 13px;
    margin-top: 10px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #818CF8;
}

QLabel {
    color: #E2E8F0;
    font-family: 'Inter', sans-serif;
}

QLineEdit, QComboBox, QSpinBox, QDateEdit {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1px solid #6366F1;
}

/* Scroll Area background */
QScrollArea {
    background-color: transparent;
    border: none;
}

/* Header Text styling */
#pageHeader {
    color: #F8FAFC;
    font-size: 22px;
    font-weight: bold;
    font-family: 'Outfit', sans-serif;
    margin-bottom: 5px;
}

/* Buttons Styles */
QPushButton {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 8px;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 16px;
    font-family: 'Inter', sans-serif;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748B;
}

QPushButton:pressed {
    background-color: #1E293B;
}

QPushButton#primaryButton {
    background-color: #4F46E5;
    border: none;
    color: #FFFFFF;
}

QPushButton#primaryButton:hover {
    background-color: #4338CA;
}

QPushButton#primaryButton:pressed {
    background-color: #312E81;
}

QPushButton#saveButton {
    background-color: #10B981;
    border: none;
    color: #FFFFFF;
}

QPushButton#saveButton:hover {
    background-color: #059669;
}

/* ScrollBar Styling */
QScrollBar:vertical {
    border: none;
    background: #0B0F19;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #1E293B;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #334155;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Custom System Status Info card */
#systemStatusCard {
    background-color: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 12px;
}

/* Scroll Area content styling to prevent white/light gray default panels on Windows */
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Tab Widget & Panel styling (fixes white/light gray background in student management) */
QTabWidget::pane {
    border: 1px solid #1E293B;
    background-color: #0F172A;
    border-radius: 12px;
}

QTabWidget > QWidget {
    background-color: #0F172A;
}

QTabBar::tab {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 4px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
}

QTabBar::tab:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #F8FAFC;
}

QTabBar::tab:selected {
    background-color: #0F172A;
    color: #818CF8;
    border-bottom: 2px solid #818CF8;
    font-weight: bold;
}

/* ComboBox dropdown popup view styling */
QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
}

/* Table Widget styling */
QTableWidget {
    background-color: #1E293B;
    color: #F8FAFC;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 8px;
}

QTableWidget::item:selected {
    background-color: #4F46E5;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 8px;
    font-weight: bold;
    border: 1px solid #1E293B;
}

/* Calendar Widget styling (for Date Filter pickers) */
QCalendarWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #0F172A;
}

QCalendarWidget QToolButton {
    color: #F8FAFC;
    background-color: transparent;
    font-weight: bold;
}

QCalendarWidget QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.05);
}

QCalendarWidget QAbstractItemView:enabled {
    color: #F8FAFC;
    background-color: #1E293B;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #475569;
}

/* QMessageBox styling (fixes light text on white background in alert popups) */
QMessageBox {
    background-color: #0F172A;
}

QMessageBox QLabel {
    color: #E2E8F0;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
}

QMessageBox QPushButton {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 6px;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 11px;
    padding: 6px 14px;
    min-width: 75px;
}

QMessageBox QPushButton:hover {
    background-color: #475569;
}

QMessageBox QPushButton:pressed {
    background-color: #1E293B;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoAttend AI - Offline Attendance Panel")
        self.resize(1100, 720)
        
        self.init_ui()
        
    def init_ui(self):
        # Main layout holds left sidebar and right central stack
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(230)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 15)
        sidebar_layout.setSpacing(20)
        
        # Logo header
        logo_layout = QVBoxLayout()
        lbl_title = QLabel("🤖 AutoAttend AI")
        lbl_title.setObjectName("sidebarTitle")
        
        lbl_sub = QLabel("InsightFace Desktop Engine")
        lbl_sub.setObjectName("sidebarSubtitle")
        
        logo_layout.addWidget(lbl_title)
        logo_layout.addWidget(lbl_sub)
        sidebar_layout.addLayout(logo_layout)
        
        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #1E293B;")
        sidebar_layout.addWidget(line)
        
        # Navigation Menu List
        self.nav_list = QListWidget()
        self.nav_list.setSpacing(4)
        
        # Add Menu Items
        menu_items = [
            ("📊 Dashboard Overview", 0),
            ("👨‍🎓 Register Student", 1),
            ("📹 Real-Time Recognition", 2),
            ("📜 Attendance Logs", 3),
            ("👤 Manage Students", 4),
            ("⚙️ System Settings", 5)
        ]
        
        for name, idx in menu_items:
            item = QListWidgetItem(name)
            self.nav_list.addItem(item)
            
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.nav_list, 1)
        
        # Divider line
        line_bottom = QFrame()
        line_bottom.setFrameShape(QFrame.Shape.HLine)
        line_bottom.setStyleSheet("background-color: #1E293B;")
        sidebar_layout.addWidget(line_bottom)
        
        # Operational Info Box
        status_box = QFrame()
        status_box.setObjectName("systemStatusCard")
        status_layout = QVBoxLayout(status_box)
        status_layout.setSpacing(5)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        lbl_status = QLabel("System Status: <b><font color='#10B981'>🟢 Operational</font></b>")
        lbl_status.setStyleSheet("font-size: 11px;")
        lbl_core = QLabel(f"Core: InsightFace v1.0.1")
        lbl_core.setStyleSheet("font-size: 10px; color: #94A3B8;")
        
        status_layout.addWidget(lbl_status)
        status_layout.addWidget(lbl_core)
        sidebar_layout.addWidget(status_box)
        
        main_layout.addWidget(sidebar)
        
        # 2. Right Central Stack
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(20, 20, 20, 15)
        right_layout.setSpacing(10)
        
        # Page title header label
        self.lbl_header = QLabel("📊 Attendance Dashboard Overview")
        self.lbl_header.setObjectName("pageHeader")
        right_layout.addWidget(self.lbl_header)
        
        # QStackedWidget page container
        self.pages_stack = QStackedWidget()
        
        # Instantiate pages
        self.page_dashboard = DashboardWidget()
        self.page_register = RegisterWidget()
        self.page_recognize = RecognizeWidget()
        self.page_history = HistoryWidget()
        self.page_student = StudentManagementWidget()
        self.page_settings = SettingsWidget()
        
        # Add to stack
        self.pages_stack.addWidget(self.page_dashboard)       # idx 0
        self.pages_stack.addWidget(self.page_register)        # idx 1
        self.pages_stack.addWidget(self.page_recognize)       # idx 2
        self.pages_stack.addWidget(self.page_history)         # idx 3
        self.pages_stack.addWidget(self.page_student)         # idx 4
        self.pages_stack.addWidget(self.page_settings)        # idx 5
        
        right_layout.addWidget(self.pages_stack, 1)
        
        # Footer
        lbl_footer = QLabel("AutoAttend AI Attendance System • Powered by InsightFace (RetinaFace + ArcFace) • Version 1.0.0")
        lbl_footer.setStyleSheet("color: #64748B; font-size: 10px;")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(lbl_footer)
        
        main_layout.addWidget(right_container, 1)
        
    def switch_page(self, index):
        # Get previous page index
        prev_index = self.pages_stack.currentIndex()
        
        # Stop webcam sessions when navigating away to prevent background usage/crashes
        if prev_index == 1: # Register Student page
            self.page_register.stop_session(silent=True)
        elif prev_index == 2: # Real-Time Recognition page
            self.page_recognize.stop_session()
            
        self.pages_stack.setCurrentIndex(index)
        
        # Update header labels
        headers = [
            "📊 Attendance Dashboard Overview",
            "👨‍🎓 Register Student & Enroll Face Profiles",
            "📹 Real-Time Face Recognition webcam",
            "📜 Attendance Logs Archive",
            "👤 Manage Students & Photographic Dataset",
            "⚙️ AutoAttend System Settings"
        ]
        if index < len(headers):
            self.lbl_header.setText(headers[index])

def main():
    # Initialize SQLite Database schema
    database.initialize_db()
    
    # Start background servers for Smartboard web view
    try:
        import smartboard_server
        smartboard_server.start_servers()
    except Exception as e:
        print(f"Could not start smartboard servers: {e}")
    
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS_STYLESHEET)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
