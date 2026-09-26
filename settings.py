from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QSpinBox, QComboBox, QLineEdit, QPushButton, QFormLayout, 
                             QGroupBox, QMessageBox, QFileDialog, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
import os

import config

class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Main layout inside scroll area in case window is small
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(15)
        
        settings = config.load_settings()
        
        # 1. Engine Settings Group
        group_engine = QGroupBox("🔍 Face Recognition & Detection Engine")
        engine_layout = QFormLayout(group_engine)
        engine_layout.setSpacing(10)
        
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setMinimum(30)
        self.slider_thresh.setMaximum(100)
        self.slider_thresh.setValue(int(float(settings.get("recognition_threshold", 0.60)) * 100))
        self.label_thresh = QLabel(f"{self.slider_thresh.value() / 100:.2f}")
        self.slider_thresh.valueChanged.connect(self.update_thresh_label)
        
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(self.slider_thresh)
        thresh_layout.addWidget(self.label_thresh)
        
        engine_layout.addRow("Confidence Threshold:", thresh_layout)
        
        self.txt_model = QLineEdit("buffalo_l (RetinaFace + ArcFace)")
        self.txt_model.setReadOnly(True)
        self.txt_model.setStyleSheet("background-color: #1E293B; color: #94A3B8;")
        engine_layout.addRow("Recognition Model:", self.txt_model)
        
        scroll_layout.addWidget(group_engine)
        
        # 2. Hardware Settings Group
        group_hw = QGroupBox("📷 Hardware & Webcam Settings")
        hw_layout = QFormLayout(group_hw)
        hw_layout.setSpacing(10)
        
        cam_source = settings.get("camera_index", 0)
        is_url = False
        try:
            int(cam_source)
        except (ValueError, TypeError):
            is_url = True

        self.combo_cam_mode = QComboBox()
        self.combo_cam_mode.addItems(["Built-in / USB Webcam (Index)", "Mobile / IP Camera (URL)"])
        self.combo_cam_mode.setCurrentIndex(1 if is_url else 0)
        hw_layout.addRow("Camera Connection Mode:", self.combo_cam_mode)
        
        self.label_cam_idx = QLabel("Camera Source Index:")
        self.spin_cam = QSpinBox()
        self.spin_cam.setMinimum(0)
        self.spin_cam.setMaximum(10)
        
        self.label_cam_url = QLabel("IP Camera URL:")
        self.txt_cam_url = QLineEdit()
        self.txt_cam_url.setPlaceholderText("e.g. http://192.168.1.50:8080/video")
        
        if is_url:
            self.spin_cam.setValue(0)
            self.txt_cam_url.setText(str(cam_source))
        else:
            self.spin_cam.setValue(int(cam_source))
            self.txt_cam_url.setText("")
            
        hw_layout.addRow(self.label_cam_idx, self.spin_cam)
        hw_layout.addRow(self.label_cam_url, self.txt_cam_url)
        
        self.lbl_camera_help = QLabel(
            "💡 <b>Tip for Mobile Camera:</b><br>"
            "1. Install the <b>IP Webcam</b> app (by Pavel Khlebovich) or similar on your phone.<br>"
            "2. Open the app, set video preferences, and tap <b>Start server</b> at the bottom.<br>"
            "3. Enter the URL shown on your phone's screen here (e.g., <i>http://192.168.1.100:8080/video</i>).<br>"
            "<i>Note: Alternatively, you can use <b>DroidCam</b> or <b>Iriun Webcam</b> on PC and Mobile to connect as a standard virtual webcam index.</i>"
        )
        self.lbl_camera_help.setWordWrap(True)
        self.lbl_camera_help.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 5px;")
        hw_layout.addRow("", self.lbl_camera_help)
        
        self.combo_res = QComboBox()
        self.combo_res.addItems(["640x480", "1280x720", "1920x1080"])
        self.combo_res.setCurrentText(settings.get("camera_resolution", "640x480"))
        hw_layout.addRow("Camera Resolution:", self.combo_res)
        
        self.combo_cam_mode.currentIndexChanged.connect(self.toggle_camera_inputs)
        # Initialize toggle state immediately
        self.toggle_camera_inputs(self.combo_cam_mode.currentIndex())
        
        scroll_layout.addWidget(group_hw)
        
        # 3. Registration Group
        group_reg = QGroupBox("👨‍🎓 Registration Settings")
        reg_layout = QFormLayout(group_reg)
        reg_layout.setSpacing(10)
        
        self.slider_capt = QSlider(Qt.Orientation.Horizontal)
        self.slider_capt.setMinimum(30)
        self.slider_capt.setMaximum(50)
        self.slider_capt.setValue(int(settings.get("capture_count", 35)))
        self.slider_capt.setTickInterval(5)
        self.slider_capt.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.label_capt = QLabel(str(self.slider_capt.value()))
        self.slider_capt.valueChanged.connect(self.update_capt_label)
        
        capt_layout = QHBoxLayout()
        capt_layout.addWidget(self.slider_capt)
        capt_layout.addWidget(self.label_capt)
        
        reg_layout.addRow("Registration Capture Count:", capt_layout)
        
        scroll_layout.addWidget(group_reg)
        
        # 4. Storage Group
        group_storage = QGroupBox("📁 Directory & Storage Paths")
        storage_layout = QFormLayout(group_storage)
        storage_layout.setSpacing(10)
        
        self.txt_dataset = QLineEdit(settings.get("dataset_dir"))
        self.txt_att = QLineEdit(settings.get("attendance_dir"))
        self.txt_models = QLineEdit(settings.get("models_dir"))
        self.txt_db = QLineEdit(settings.get("database_path"))
        self.txt_pkl = QLineEdit(settings.get("encodings_path"))
        
        storage_layout.addRow("Dataset Directory:", self.create_path_row(self.txt_dataset, is_dir=True))
        storage_layout.addRow("Attendance Directory:", self.create_path_row(self.txt_att, is_dir=True))
        storage_layout.addRow("Models Directory:", self.create_path_row(self.txt_models, is_dir=True))
        storage_layout.addRow("SQLite Database Path:", self.create_path_row(self.txt_db, is_dir=False))
        storage_layout.addRow("Encodings File Path:", self.create_path_row(self.txt_pkl, is_dir=False))
        
        scroll_layout.addWidget(group_storage)
        
        # 5. Interface Group
        group_ui = QGroupBox("🎨 User Interface Settings")
        ui_layout = QFormLayout(group_ui)
        ui_layout.setSpacing(10)
        
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"])
        self.combo_theme.setCurrentText(settings.get("theme", "dark"))
        ui_layout.addRow("Visual Theme Mode:", self.combo_theme)
        
        scroll_layout.addWidget(group_ui)
        
        # Save Button
        self.btn_save = QPushButton("💾 Save Configurations")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self.save_configurations)
        scroll_layout.addWidget(self.btn_save)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
    def update_thresh_label(self, val):
        self.label_thresh.setText(f"{val / 100:.2f}")
        
    def update_capt_label(self, val):
        self.label_capt.setText(str(val))
        
    def create_path_row(self, line_edit, is_dir=True):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self.browse_path(line_edit, is_dir))
        layout.addWidget(btn)
        return row
        
    def browse_path(self, line_edit, is_dir=True):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text())
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Select File Location", line_edit.text(), "All Files (*.*)")
            
        if path:
            line_edit.setText(os.path.normpath(path))
            
    def toggle_camera_inputs(self, index):
        is_webcam = (index == 0)
        self.label_cam_idx.setVisible(is_webcam)
        self.spin_cam.setVisible(is_webcam)
        self.label_cam_url.setVisible(not is_webcam)
        self.txt_cam_url.setVisible(not is_webcam)
        self.lbl_camera_help.setVisible(not is_webcam)
            
    def save_configurations(self):
        if self.combo_cam_mode.currentIndex() == 0:
            cam_idx = self.spin_cam.value()
        else:
            cam_idx = self.txt_cam_url.text().strip()
            if not cam_idx:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid IP Camera URL.")
                return

        new_settings = {
            "recognition_threshold": self.slider_thresh.value() / 100,
            "camera_index": cam_idx,
            "camera_resolution": self.combo_res.currentText(),
            "capture_count": self.slider_capt.value(),
            "dataset_dir": self.txt_dataset.text(),
            "attendance_dir": self.txt_att.text(),
            "models_dir": self.txt_models.text(),
            "database_path": self.txt_db.text(),
            "encodings_path": self.txt_pkl.text(),
            "theme": self.combo_theme.currentText()
        }
        
        success = config.save_settings(new_settings)
        if success:
            # Sync back config runtime variables
            config.RECOGNITION_THRESHOLD = new_settings["recognition_threshold"]
            # Convert config.CAMERA_INDEX dynamically
            try:
                config.CAMERA_INDEX = int(new_settings["camera_index"])
            except (ValueError, TypeError):
                config.CAMERA_INDEX = str(new_settings["camera_index"]).strip()
                
            config.CAMERA_RESOLUTION = new_settings["camera_resolution"]
            config.CAPTURE_COUNT = new_settings["capture_count"]
            config.DATASET_DIR = new_settings["dataset_dir"]
            config.ATTENDANCE_DIR = new_settings["attendance_dir"]
            config.MODELS_DIR = new_settings["models_dir"]
            config.DATABASE_PATH = new_settings["database_path"]
            config.ENCODINGS_PATH = new_settings["encodings_path"]
            config.THEME = new_settings["theme"]
            
            # Ensure folders exist
            for p in [config.DATASET_DIR, config.ATTENDANCE_DIR, config.MODELS_DIR]:
                os.makedirs(p, exist_ok=True)
                
            QMessageBox.information(self, "Success", "Configurations saved successfully! Changes have been loaded. Re-open pages to fully apply new directory paths.")
        else:
            QMessageBox.critical(self, "Error", "Failed to write settings.json configuration file.")
