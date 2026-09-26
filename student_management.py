from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTabWidget, QGroupBox, QMessageBox, 
                             QFormLayout, QScrollArea, QGridLayout, QSplitter, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
import os
import shutil

import database
from utils import recognizer, load_all_encodings, save_all_encodings
import config

class StudentManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # 1. Directory Tab
        self.tab_view = QWidget()
        self.init_view_tab()
        self.tabs.addTab(self.tab_view, "👥 View All Students")
        
        # 2. Profile & Gallery Tab
        self.tab_profile = QWidget()
        self.init_profile_tab()
        self.tabs.addTab(self.tab_profile, "🖼️ Profile & Gallery")
        
        # 3. Edit Tab
        self.tab_edit = QWidget()
        self.init_edit_tab()
        self.tabs.addTab(self.tab_edit, "✏️ Edit Details")
        
        # 4. Delete Tab
        self.tab_delete = QWidget()
        self.init_delete_tab()
        self.tabs.addTab(self.tab_delete, "🗑️ Delete Student")
        
        layout.addWidget(self.tabs)
        
    # ----------------------------------------------------
    # Tab 1: View Students
    # ----------------------------------------------------
    def init_view_tab(self):
        layout = QVBoxLayout(self.tab_view)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search Name or Student ID...")
        self.txt_search.textChanged.connect(self.load_directory)
        search_layout.addWidget(QLabel("Search Student:"))
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)
        
        # Directory Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Student ID", "Full Name", "Roll Number", "Class", "Section", "Gender", "Phone", "Registered At"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #1E293B; color: #F8FAFC; gridline-color: #334155;")
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self.load_directory()
        
    def load_directory(self):
        query = self.txt_search.text().strip().lower()
        students = database.get_all_students()
        
        filtered = []
        for s in students:
            if not query or query in s["name"].lower() or query in s["student_id"].lower():
                filtered.append(s)
                
        self.table.setRowCount(0)
        if not filtered:
            return
            
        self.table.setRowCount(len(filtered))
        for r_idx, s in enumerate(filtered):
            self.table.setItem(r_idx, 0, QTableWidgetItem(s["student_id"]))
            self.table.setItem(r_idx, 1, QTableWidgetItem(s["name"]))
            self.table.setItem(r_idx, 2, QTableWidgetItem(s["roll_number"]))
            self.table.setItem(r_idx, 3, QTableWidgetItem(s["class_name"]))
            self.table.setItem(r_idx, 4, QTableWidgetItem(s["section"]))
            self.table.setItem(r_idx, 5, QTableWidgetItem(s["gender"]))
            self.table.setItem(r_idx, 6, QTableWidgetItem(s["phone"] if s["phone"] else "N/A"))
            self.table.setItem(r_idx, 7, QTableWidgetItem(s["created_at"]))
            
    # ----------------------------------------------------
    # Tab 2: Profile & Gallery
    # ----------------------------------------------------
    def init_profile_tab(self):
        layout = QVBoxLayout(self.tab_profile)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Combo selection
        sel_layout = QHBoxLayout()
        self.combo_profile = QComboBox()
        self.combo_profile.currentIndexChanged.connect(self.load_profile_details)
        sel_layout.addWidget(QLabel("Select Student Profile:"))
        sel_layout.addWidget(self.combo_profile, 1)
        layout.addLayout(sel_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Avatar and Info Labels
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.label_avatar = QLabel()
        self.label_avatar.setFixedSize(160, 160)
        self.label_avatar.setStyleSheet("background-color: #0F172A; border: 2px solid #1E293B; border-radius: 80px;")
        self.label_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.label_avatar, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.label_details = QLabel("Select a student to load details.")
        self.label_details.setStyleSheet("font-size: 13px; line-height: 20px; padding: 10px;")
        self.label_details.setWordWrap(True)
        left_layout.addWidget(self.label_details)
        left_layout.addStretch()
        
        # Right side: Grid Photo Gallery
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("🖼️ Facial Landmark Templates Gallery (Saved Angles):"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gallery_widget = QWidget()
        self.gallery_grid = QGridLayout(self.gallery_widget)
        self.gallery_grid.setSpacing(10)
        scroll.setWidget(self.gallery_widget)
        
        right_layout.addWidget(scroll)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter)
        
    def refresh_combos(self):
        students = database.get_all_students()
        names_list = [f"{s['name']} ({s['student_id']})" for s in students]
        
        self.combo_profile.clear()
        self.combo_profile.addItems(names_list)
        
        self.combo_edit.clear()
        self.combo_edit.addItems(names_list)
        
        self.combo_delete.clear()
        self.combo_delete.addItems(names_list)
        
    def load_profile_details(self):
        # Clear gallery
        for i in reversed(range(self.gallery_grid.count())): 
            self.gallery_grid.itemAt(i).widget().setParent(None)
            
        self.label_avatar.clear()
        self.label_avatar.setText("No Photo")
        self.label_details.setText("Select a student to load details.")
        
        if self.combo_profile.currentIndex() == -1:
            return
            
        student_str = self.combo_profile.currentText()
        student_id = student_str.split(" (")[-1][:-1]
        
        s = database.get_student(student_id)
        if not s:
            return
            
        self.label_details.setText(
            f"<b>Full Name:</b> {s['name']}<br>"
            f"<b>Student ID:</b> {s['student_id']}<br>"
            f"<b>Roll Number:</b> {s['roll_number']}<br>"
            f"<b>Class:</b> {s['class_name']}<br>"
            f"<b>Section:</b> {s['section']}<br>"
            f"<b>Gender:</b> {s['gender']}<br>"
            f"<b>Phone:</b> {s['phone'] if s['phone'] else 'N/A'}<br>"
            f"<b>Enrolled On:</b> {s['created_at']}"
        )
        
        # Load images
        student_dir = os.path.join(config.DATASET_DIR, student_id)
        if not os.path.exists(student_dir):
            return
            
        images = [img for img in os.listdir(student_dir) if img.endswith(".jpg") and img != "profile.jpg"]
        if not images and not os.path.exists(os.path.join(student_dir, "profile.jpg")):
            return
            
        # Set avatar as profile.jpg, fallback to first image if not found
        profile_path = os.path.join(student_dir, "profile.jpg")
        if os.path.exists(profile_path):
            avatar_path = profile_path
        else:
            avatar_path = os.path.join(student_dir, sorted(images)[0])
            
        pix = QPixmap(avatar_path)
        if not pix.isNull():
            self.label_avatar.setPixmap(pix.scaled(self.label_avatar.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            
        # Grid photo library
        for idx, img_file in enumerate(sorted(images)):
            img_path = os.path.join(student_dir, img_file)
            img_label = QLabel()
            img_label.setFixedSize(90, 90)
            img_label.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px;")
            img_pix = QPixmap(img_path)
            if not img_pix.isNull():
                img_label.setPixmap(img_pix.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            
            row = idx // 4
            col = idx % 4
            self.gallery_grid.addWidget(img_label, row, col)
            
    # ----------------------------------------------------
    # Tab 3: Edit Info
    # ----------------------------------------------------
    def init_edit_tab(self):
        layout = QVBoxLayout(self.tab_edit)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.combo_edit = QComboBox()
        self.combo_edit.currentIndexChanged.connect(self.populate_edit_form)
        layout.addWidget(QLabel("Select Student to Edit:"))
        layout.addWidget(self.combo_edit)
        
        group_edit = QGroupBox("✏️ Edit Credentials")
        form_layout = QFormLayout(group_edit)
        form_layout.setSpacing(12)
        
        self.edit_name = QLineEdit()
        form_layout.addRow("Full Name:", self.edit_name)
        
        self.edit_roll = QLineEdit()
        form_layout.addRow("Roll Number:", self.edit_roll)
        
        self.edit_class = QComboBox()
        self.edit_class.addItems([f"Class {i}" for i in range(1, 11)])
        form_layout.addRow("Class:", self.edit_class)
        
        self.edit_sec = QComboBox()
        self.edit_sec.addItems(["N/A", "A", "B", "C", "D", "E"])
        form_layout.addRow("Section:", self.edit_sec)
        
        self.edit_gender = QComboBox()
        self.edit_gender.addItems(["Male", "Female", "Other"])
        form_layout.addRow("Gender:", self.edit_gender)
        
        self.edit_phone = QLineEdit()
        form_layout.addRow("Phone Number:", self.edit_phone)
        
        layout.addWidget(group_edit)
        
        self.btn_save_edit = QPushButton("💾 Save Profile Changes")
        self.btn_save_edit.setObjectName("primaryButton")
        self.btn_save_edit.setMinimumHeight(40)
        self.btn_save_edit.clicked.connect(self.save_student_edit)
        layout.addWidget(self.btn_save_edit)
        layout.addStretch()
        
    def populate_edit_form(self):
        if self.combo_edit.currentIndex() == -1:
            return
            
        student_str = self.combo_edit.currentText()
        student_id = student_str.split(" (")[-1][:-1]
        
        s = database.get_student(student_id)
        if not s:
            return
            
        self.edit_name.setText(s["name"])
        self.edit_roll.setText(s["roll_number"])
        self.edit_class.setCurrentText(s["class_name"])
        self.edit_sec.setCurrentText(s["section"])
        self.edit_gender.setCurrentText(s["gender"])
        self.edit_phone.setText(s["phone"] if s["phone"] else "")
        
    def save_student_edit(self):
        if self.combo_edit.currentIndex() == -1:
            return
            
        student_str = self.combo_edit.currentText()
        student_id = student_str.split(" (")[-1][:-1]
        
        name = self.edit_name.text().strip()
        roll = self.edit_roll.text().strip()
        class_name = self.edit_class.currentText()
        section = self.edit_sec.currentText()
        gender = self.edit_gender.currentText()
        phone = self.edit_phone.text().strip()
        
        if not name or not roll:
            QMessageBox.warning(self, "Input Error", "Name and Roll Number cannot be empty.")
            return
            
        success = database.update_student(
            student_id=student_id,
            name=name,
            roll_number=roll,
            class_name=class_name,
            section=section,
            gender=gender,
            phone=phone if phone else None
        )
        
        if success:
            QMessageBox.information(self, "Updated", "Student details updated successfully.")
            self.load_directory()
            self.refresh_combos()
        else:
            QMessageBox.critical(self, "Error", "Failed to update profile. Roll number must be unique.")
            
    # ----------------------------------------------------
    # Tab 4: Delete Student
    # ----------------------------------------------------
    def init_delete_tab(self):
        layout = QVBoxLayout(self.tab_delete)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.combo_delete = QComboBox()
        layout.addWidget(QLabel("Select Student to Permanently Delete:"))
        layout.addWidget(self.combo_delete)
        
        group_warn = QGroupBox("⚠️ Crucial Notice")
        warn_layout = QVBoxLayout(group_warn)
        warn_layout.addWidget(QLabel(
            "Deleting this student profile will permanently wipe:\n"
            "  1. Database record directory logs in SQLite.\n"
            "  2. All 35 captured angle face files stored on disk.\n"
            "  3. Embedded pickle key files in encodings_arcface.pkl (locks check-in checks)."
        ))
        layout.addWidget(group_warn)
        
        self.btn_delete = QPushButton("🗑️ Permanently Delete Profile")
        self.btn_delete.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        self.btn_delete.setMinimumHeight(45)
        self.btn_delete.clicked.connect(self.delete_student_profile)
        layout.addWidget(self.btn_delete)
        
        layout.addStretch()
        
    def delete_student_profile(self):
        if self.combo_delete.currentIndex() == -1:
            return
            
        student_str = self.combo_delete.currentText()
        student_id = student_str.split(" (")[-1][:-1]
        
        confirm = QMessageBox.critical(
            self, "Permanently Delete Student", 
            f"Are you sure you want to completely erase student ID '{student_id}' and all their photo template archives?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            db_success = database.delete_student(student_id)
            if db_success:
                # Delete folder
                student_dir = os.path.join(config.DATASET_DIR, student_id)
                if os.path.exists(student_dir):
                    try:
                        shutil.rmtree(student_dir)
                    except Exception as e:
                        print(f"Error removing dataset folder: {e}")
                        
                # Remove from pickle
                encodings = load_all_encodings()
                if student_id in encodings:
                    del encodings[student_id]
                    save_all_encodings(encodings)
                    
                # Reload model cache
                recognizer.load_encodings_cache()
                
                QMessageBox.information(self, "Deleted", "Student profile completely erased from system.")
                
                self.load_directory()
                self.refresh_combos()
            else:
                QMessageBox.critical(self, "Database Error", "Failed to delete student records from SQLite registry.")
                
    def showEvent(self, event):
        # Refresh widgets list when user selects this main tab
        self.load_directory()
        self.refresh_combos()
        event.accept()
