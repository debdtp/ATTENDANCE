import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGroupBox, QGridLayout, QScrollArea, QListWidget, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import database
import config

class PresentStudentCard(QFrame):
    def __init__(self, name, student_id, class_name, section, time_str, confidence, parent=None):
        super().__init__(parent)
        self.setObjectName("presentCard")
        self.setStyleSheet(
            "#presentCard {"
            "  background-color: #1E293B;"
            "  border: 1px solid #334155;"
            "  border-radius: 12px;"
            "}"
        )
        self.setFixedSize(140, 195)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Profile image (circular)
        self.lbl_pic = QLabel()
        self.lbl_pic.setFixedSize(70, 70)
        self.lbl_pic.setStyleSheet("background-color: #0F172A; border-radius: 35px; border: 1px solid #4F46E5;")
        self.lbl_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load profile picture
        student_dir = os.path.join(config.DATASET_DIR, student_id)
        profile_path = os.path.join(student_dir, "profile.jpg")
        
        pix = QPixmap()
        if os.path.exists(profile_path):
            pix.load(profile_path)
        else:
            if os.path.exists(student_dir):
                images = [img for img in os.listdir(student_dir) if img.endswith(".jpg") and img != "profile.jpg"]
                if images:
                    pix.load(os.path.join(student_dir, sorted(images)[0]))
                    
        if not pix.isNull():
            self.lbl_pic.setPixmap(pix.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_pic.setText("👤")
            self.lbl_pic.setStyleSheet("background-color: #0F172A; border-radius: 35px; color: #94A3B8; font-size: 28px; border: 1px solid #334155; padding-bottom: 2px;")
            
        layout.addWidget(self.lbl_pic, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Student Name
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 11px;")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(True)
        layout.addWidget(lbl_name)
        
        # Class / Sec
        sec_str = f" - {section}" if section and section != "N/A" else ""
        lbl_class = QLabel(f"{class_name}{sec_str}")
        lbl_class.setStyleSheet("color: #94A3B8; font-size: 10px;")
        lbl_class.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_class)
        
        # Time
        lbl_time = QLabel(time_str)
        lbl_time.setStyleSheet("color: #10B981; font-weight: bold; font-size: 10px;")
        lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_time)
        
        # Confidence
        lbl_conf = QLabel(f"Match: {confidence}")
        lbl_conf.setStyleSheet("color: #64748B; font-size: 9px;")
        lbl_conf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_conf)

class MetricCard(QGroupBox):
    def __init__(self, title, value, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(
            "QGroupBox {"
            "  background-color: rgba(30, 41, 59, 0.45);"
            "  border: 1px solid rgba(255, 255, 255, 0.08);"
            "  border-radius: 12px;"
            "  margin-top: 15px;"
            "  font-weight: bold;"
            "  color: #94A3B8;"
            "  font-size: 11px;"
            "  text-transform: uppercase;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  subcontrol-position: top left;"
            "  padding: 5px 10px;"
            "}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 25, 15, 15)
        
        self.lbl_val = QLabel(str(value))
        font = QFont("Outfit", 20, QFont.Weight.Bold)
        self.lbl_val.setFont(font)
        self.lbl_val.setStyleSheet("color: #F8FAFC;")
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_val)
        
    def set_value(self, val):
        self.lbl_val.setText(str(val))

class DashboardWidget(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.init_ui()
        
    def init_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. Metrics Cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)
        
        self.card_total = MetricCard("👥 Total Students", "0")
        self.card_present = MetricCard("✅ Present Today", "0")
        self.card_unknown = MetricCard("❓ Unknowns Today", "0")
        self.card_rate = MetricCard("📈 Attendance %", "0.0%")
        self.card_acc = MetricCard("🎯 Accuracy Proxy", "0.0%")
        
        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_present)
        cards_layout.addWidget(self.card_unknown)
        cards_layout.addWidget(self.card_rate)
        cards_layout.addWidget(self.card_acc)
        
        layout.addLayout(cards_layout)
        
        # 2. Main content layout (Today's Present Students & Recent Activities)
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(15)
        
        # Today's present students gallery
        group_table = QGroupBox("📋 Today's Present Students")
        table_vbox = QVBoxLayout(group_table)
        
        self.scroll_gallery = QScrollArea()
        self.scroll_gallery.setWidgetResizable(True)
        self.scroll_gallery.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_gallery.setStyleSheet("background-color: transparent;")
        
        self.gallery_content = QWidget()
        self.gallery_content.setStyleSheet("background-color: transparent;")
        self.gallery_layout = QGridLayout(self.gallery_content)
        self.gallery_layout.setSpacing(10)
        self.gallery_layout.setContentsMargins(5, 5, 5, 5)
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll_gallery.setWidget(self.gallery_content)
        self.scroll_gallery.setMinimumHeight(420)
        table_vbox.addWidget(self.scroll_gallery)
        main_content_layout.addWidget(group_table, 2)
        
        # Recent activities log
        group_activities = QGroupBox("⚡ Recent Activities Log")
        act_vbox = QVBoxLayout(group_activities)
        self.list_activity = QListWidget()
        self.list_activity.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border: none;")
        self.list_activity.setMinimumHeight(420)
        act_vbox.addWidget(self.list_activity)
        main_content_layout.addWidget(group_activities, 1)
        
        layout.addLayout(main_content_layout)
        
        self.setWidget(content)
        self.refresh_dashboard()
        
    def refresh_dashboard(self):
        students = database.get_all_students()
        attendance_today = database.get_attendance_today()
        unknowns_today = database.get_unknown_detections_today()
        
        total_students = len(students)
        present_today = len(attendance_today)
        
        # Fetch stats
        disp_total = total_students
        disp_present = present_today
        disp_unknown = unknowns_today
        attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0.0
        
        if present_today > 0:
            accuracy = np.mean([log["confidence"] for log in attendance_today]) * 100
        else:
            accuracy = 0.0
                
        # Card updates
        self.card_total.set_value(str(disp_total))
        self.card_present.set_value(str(disp_present))
        self.card_unknown.set_value(str(disp_unknown))
        self.card_rate.set_value(f"{attendance_rate:.1f}%")
        self.card_acc.set_value(f"{accuracy:.1f}%")
        
        # Plots logic removed (graphs disabled for simplified UI layout)
        
        # 3. Load Bottom Gallery Cards
        # Clear existing layout items
        for i in reversed(range(self.gallery_layout.count())):
            w = self.gallery_layout.itemAt(i).widget()
            if w is not None:
                w.setParent(None)
                
        for idx, row in enumerate(attendance_today):
            conf_pct = f"{row['confidence'] * 100:.1f}%"
            card = PresentStudentCard(
                name=row["name"],
                student_id=row["student_id"],
                class_name=row["class_name"],
                section=row["section"],
                time_str=row["time"],
                confidence=conf_pct
            )
            row_idx = idx // 3
            col_idx = idx % 3
            self.gallery_layout.addWidget(card, row_idx, col_idx)
            
        if not attendance_today:
            lbl_no_one = QLabel("No students present today yet.")
            lbl_no_one.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold; padding: 20px;")
            self.gallery_layout.addWidget(lbl_no_one, 0, 0)
                
        # 4. Load Bottom List Activities
        self.list_activity.clear()
        activities = []
        for row in attendance_today[:5]:
            activities.append(f"{row['time']} - 🟢 {row['name']} checked in")
            
        # Get unknowns
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT time, confidence FROM unknown_log ORDER BY date DESC, time DESC LIMIT 5")
        u_rows = cur.fetchall()
        conn.close()
        for u in u_rows:
            activities.append(f"{u['time']} - 🔴 Unknown face detected (sim {u['confidence']*100:.1f}%)")
            
        # Sort by time string
        activities = sorted(activities, reverse=True)[:5]
        if activities:
            self.list_activity.addItems(activities)
        else:
            self.list_activity.addItem("No activities recorded today yet.")
                
    def showEvent(self, event):
        # Auto-refresh whenever the page is selected/stacked in the view
        self.refresh_dashboard()
        event.accept()
