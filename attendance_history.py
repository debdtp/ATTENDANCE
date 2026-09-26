from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QDateEdit, QFormLayout, QGroupBox, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QDate
import pandas as pd
import os

import database

class HistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. Filters Group
        group_filters = QGroupBox("🔍 Search & Filter Attendance Logs")
        filter_layout = QHBoxLayout(group_filters)
        
        # Column 1
        col1 = QVBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search Name or ID...")
        col1.addWidget(QLabel("Student Search:"))
        col1.addWidget(self.txt_search)
        
        self.combo_class = QComboBox()
        self.combo_class.addItem("All")
        col1.addWidget(QLabel("Class Filter:"))
        col1.addWidget(self.combo_class)
        
        filter_layout.addLayout(col1)
        
        # Column 2
        col2 = QVBoxLayout()
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(-7))
        col2.addWidget(QLabel("Start Date:"))
        col2.addWidget(self.date_start)
        
        self.combo_sec = QComboBox()
        self.combo_sec.addItem("All")
        col2.addWidget(QLabel("Section Filter:"))
        col2.addWidget(self.combo_sec)
        
        filter_layout.addLayout(col2)
        
        # Column 3
        col3 = QVBoxLayout()
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        col3.addWidget(QLabel("End Date:"))
        col3.addWidget(self.date_end)
        
        self.btn_search = QPushButton("🔍 Apply Filters")
        self.btn_search.setObjectName("primaryButton")
        self.btn_search.setMinimumHeight(35)
        self.btn_search.clicked.connect(self.load_data)
        col3.addWidget(QLabel(""))
        col3.addWidget(self.btn_search)
        
        filter_layout.addLayout(col3)
        layout.addWidget(group_filters)
        
        # 2. Table Results
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Record ID", "Student ID", "Student Name", "Class", "Section", "Date", "Time", "Status", "Confidence"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #1E293B; color: #F8FAFC; gridline-color: #334155;")
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # 3. Actions Row
        actions_layout = QHBoxLayout()
        
        # Left Actions: Exports
        group_exports = QGroupBox("📥 Export Reports")
        exports_layout = QHBoxLayout(group_exports)
        
        self.btn_csv = QPushButton("📄 Export to CSV")
        self.btn_csv.setMinimumHeight(35)
        self.btn_csv.clicked.connect(self.export_csv)
        exports_layout.addWidget(self.btn_csv)
        
        self.btn_xlsx = QPushButton("📊 Export to Excel")
        self.btn_xlsx.setMinimumHeight(35)
        self.btn_xlsx.clicked.connect(self.export_excel)
        exports_layout.addWidget(self.btn_xlsx)
        
        actions_layout.addWidget(group_exports, 3)
        
        # Right Actions: Delete Record & Clear Logs
        group_delete = QGroupBox("🗑️ Admin Log Control")
        delete_layout = QHBoxLayout(group_delete)
        
        self.spin_del_id = QLineEdit()
        self.spin_del_id.setPlaceholderText("Record ID")
        self.spin_del_id.setMaximumWidth(90)
        delete_layout.addWidget(self.spin_del_id)
        
        self.btn_delete = QPushButton("❌ Delete Log")
        self.btn_delete.setStyleSheet("background-color: #EF4444; color: white;")
        self.btn_delete.setMinimumHeight(35)
        self.btn_delete.clicked.connect(self.delete_log_record)
        delete_layout.addWidget(self.btn_delete)
        
        self.btn_clear_all = QPushButton("🚨 Clear All Logs")
        self.btn_clear_all.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold;")
        self.btn_clear_all.setMinimumHeight(35)
        self.btn_clear_all.clicked.connect(self.clear_all_logs)
        delete_layout.addWidget(self.btn_clear_all)
        
        actions_layout.addWidget(group_delete, 4)
        
        layout.addLayout(actions_layout)
        
        # Initial loads
        self.load_filters()
        self.load_data()
        
    def load_filters(self):
        # Fetch unique class & section lists from registered students
        students = database.get_all_students()
        classes = sorted(list(set([s["class_name"] for s in students])))
        sections = sorted(list(set([s["section"] for s in students])))
        
        self.combo_class.clear()
        self.combo_class.addItem("All")
        self.combo_class.addItems(classes)
        
        self.combo_sec.clear()
        self.combo_sec.addItem("All")
        self.combo_sec.addItems(sections)
        
    def load_data(self):
        student_query = self.txt_search.text().strip()
        class_filter = self.combo_class.currentText()
        section_filter = self.combo_sec.currentText()
        start_str = self.date_start.date().toString("yyyy-MM-dd")
        end_str = self.date_end.date().toString("yyyy-MM-dd")
        
        # Query
        self.df_data = database.query_attendance_history(
            student_query=student_query if student_query else None,
            start_date=start_str,
            end_date=end_str,
            class_name=class_filter,
            section=section_filter
        )
        
        # Load table
        self.table.setRowCount(0)
        if self.df_data.empty:
            return
            
        self.table.setRowCount(len(self.df_data))
        for r_idx, row in self.df_data.iterrows():
            conf_str = f"{row['confidence'] * 100:.1f}%"
            
            self.table.setItem(r_idx, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(r_idx, 1, QTableWidgetItem(str(row["student_id"])))
            self.table.setItem(r_idx, 2, QTableWidgetItem(row["name"]))
            self.table.setItem(r_idx, 3, QTableWidgetItem(row["class_name"]))
            self.table.setItem(r_idx, 4, QTableWidgetItem(row["section"]))
            self.table.setItem(r_idx, 5, QTableWidgetItem(row["date"]))
            self.table.setItem(r_idx, 6, QTableWidgetItem(row["time"]))
            self.table.setItem(r_idx, 7, QTableWidgetItem(row["status"]))
            self.table.setItem(r_idx, 8, QTableWidgetItem(conf_str))
            
    def export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export Error", "No data logs are loaded to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.df_data.to_csv(file_path, index=False)
                QMessageBox.information(self, "Export Success", f"Logs exported to {os.path.basename(file_path)} successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save CSV file: {e}")
                
    def export_excel(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export Error", "No data logs are loaded to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "", "Excel Workbook (*.xlsx)")
        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    self.df_data.to_excel(writer, index=False, sheet_name='Attendance Logs')
                QMessageBox.information(self, "Export Success", f"Logs exported to {os.path.basename(file_path)} successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save Excel file: {e}")
                
    def delete_log_record(self):
        rec_id_str = self.spin_del_id.text().strip()
        if not rec_id_str:
            QMessageBox.warning(self, "Input Error", "Please provide a valid Record ID from the logs table.")
            return
            
        try:
            rec_id = int(rec_id_str)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Record ID must be numeric.")
            return
            
        # Verify if ID is loaded
        if self.df_data.empty or rec_id not in self.df_data["id"].values:
            QMessageBox.warning(self, "Validation Error", f"Record ID {rec_id} was not found in the filtered records listed above.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to permanently delete attendance record ID {rec_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success = database.delete_attendance_record(rec_id)
            if success:
                QMessageBox.information(self, "Deleted", f"Record ID {rec_id} deleted successfully.")
                self.spin_del_id.clear()
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Could not delete record from database.")
                
    def clear_all_logs(self):
        confirm = QMessageBox.warning(
            self, "Clear All Logs",
            "⚠️ WARNING: Are you absolutely sure you want to permanently erase ALL attendance history logs from the system? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success = database.clear_all_attendance_logs()
            if success:
                QMessageBox.information(self, "Success", "All attendance records have been permanently cleared.")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to clear attendance records from the database.")
