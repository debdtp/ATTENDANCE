from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QPushButton, QProgressBar, QFormLayout, 
                             QGroupBox, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import os
import time
import numpy as np
import shutil
from concurrent.futures import ThreadPoolExecutor
import queue
import threading

import database
from utils import recognizer, load_all_encodings, save_all_encodings, _open_camera_with_retry
import config

def _camera_reader_loop(cap, frame_queue, running_flag):
    while running_flag[0]:
        try:
            ret, frame = cap.read()
            if not ret:
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                frame_queue.put(None)
                break
            
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put(frame)
        except Exception:
            break

# Angles configuration: 10 captures per angle = 70 total
ANGLES = [
    {"name": "Front (Neutral)", "count": 10, "instruction": "Look directly at the camera with a neutral expression."},
    {"name": "Turn Left", "count": 10, "instruction": "Slowly turn your head to the left side."},
    {"name": "Turn Right", "count": 10, "instruction": "Slowly turn your head to the right side."},
    {"name": "Look Up", "count": 10, "instruction": "Tilt your head slightly upwards."},
    {"name": "Look Down", "count": 10, "instruction": "Tilt your head slightly downwards."},
    {"name": "Smile", "count": 10, "instruction": "Look at the camera and give a big smile!"},
    {"name": "Neutral (Blink)", "count": 10, "instruction": "Relax, blink normally and look at the camera."}
]

class PreviewThread(QThread):
    frame_ready = pyqtSignal(QImage, np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def stop(self):
        self.running = False
        
    def run(self):
        cap = _open_camera_with_retry(config.CAMERA_INDEX)
        if cap is None:
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        running_flag = [True]
        frame_queue = queue.Queue(maxsize=1)
        
        reader_thread = threading.Thread(
            target=_camera_reader_loop,
            args=(cap, frame_queue, running_flag),
            daemon=True
        )
        reader_thread.start()
        
        try:
            while self.running:
                try:
                    frame = frame_queue.get(timeout=0.03)
                    if frame is None:
                        break
                    
                    frame = cv2.flip(frame, 1)
                    
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                    
                    self.frame_ready.emit(qt_img, frame)
                except queue.Empty:
                    continue
        finally:
            running_flag[0] = False
            threading.Thread(target=cap.release, daemon=True).start()

class RegisterThread(QThread):
    # Signals to communicate back to the GUI thread
    frame_ready = pyqtSignal(QImage)
    progress_updated = pyqtSignal(int, str, str) # current_count, angle_name, instruction_text
    capture_finished = pyqtSignal(bool, str, list) # success, message, list_of_embeddings
    
    def __init__(self, student_id):
        super().__init__()
        self.student_id = student_id
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.inference_future = None
        self.inference_busy = False
        self.inference_frame = None
        
    def stop(self):
        self.running = False
        
    def run_inference(self, frame_copy):
        try:
            return recognizer.extract_faces(frame_copy)
        except Exception as e:
            print(f"Error in background registration inference: {e}")
            return []
            
    def run(self):
        # Open webcam
        cap = _open_camera_with_retry(config.CAMERA_INDEX)
        if cap is None:
            self.capture_finished.emit(False, "Could not access the webcam.", [])
            return
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Ensure student dataset folder exists
        student_dir = os.path.join(config.DATASET_DIR, self.student_id)
        os.makedirs(student_dir, exist_ok=True)
        
        total_images = config.CAPTURE_COUNT
        captured_images = 0
        current_angle_idx = 0
        angle_captured = 0
        embeddings_list = []
        first_face_checked = False
        
        # Track when the last capture happened to introduce a natural gap between captures
        last_capture_time = 0.0
        capture_interval = 0.35 # 350ms delay between captures to let user change expressions/angles
        
        latest_bbox = None
        status_text = "Aligning Camera"
        status_color = (0, 165, 255) # Orange
        
        running_flag = [True]
        frame_queue = queue.Queue(maxsize=1)
        
        reader_thread = threading.Thread(
            target=_camera_reader_loop,
            args=(cap, frame_queue, running_flag),
            daemon=True
        )
        reader_thread.start()
        
        try:
            while self.running and captured_images < total_images:
                # Check angle transition
                current_angle = ANGLES[current_angle_idx]
                if angle_captured >= current_angle["count"]:
                    current_angle_idx += 1
                    if current_angle_idx >= len(ANGLES):
                        break
                    current_angle = ANGLES[current_angle_idx]
                    angle_captured = 0
                
                try:
                    frame = frame_queue.get(timeout=0.03)
                    if frame is None:
                        self.capture_finished.emit(False, "Failed to read frame from webcam.", [])
                        break
                except queue.Empty:
                    continue
                    
                # Mirror view
                frame = cv2.flip(frame, 1)
                
                # Copy for drawing
                draw_frame = frame.copy()
                
                # Emit details to update progress widgets
                self.progress_updated.emit(captured_images, current_angle["name"], current_angle["instruction"])
                
                # Check if async inference finished
                if self.inference_future is not None and self.inference_future.done():
                    try:
                        faces = self.inference_future.result()
                        # Process face results
                        if len(faces) == 0:
                            status_text = "No Face Detected"
                            status_color = (0, 0, 255) # Red
                            latest_bbox = None
                        elif len(faces) > 1:
                            status_text = "Multiple Faces Detected"
                            status_color = (0, 165, 255) # Orange
                            latest_bbox = None
                        else:
                            status_text = "Capturing Templates"
                            status_color = (0, 255, 0) # Green
                            latest_bbox = faces[0]["bbox"]
                            
                            # Check capture delay/interval
                            curr_time = time.time()
                            if curr_time - last_capture_time >= capture_interval:
                                embedding = faces[0]["normed_embedding"]
                                if embedding is not None:
                                    if not first_face_checked:
                                        matched_id, similarity = recognizer.match_face(embedding, config.RECOGNITION_THRESHOLD)
                                        if matched_id:
                                            matched_student = database.get_student(matched_id)
                                            matched_name = matched_student["name"] if matched_student else "Unknown"
                                            self.capture_finished.emit(
                                                False,
                                                f"Duplicate Face: This face is already registered under '{matched_name}' (ID: '{matched_id}').",
                                                []
                                            )
                                            return
                                        first_face_checked = True
 
                                    # Save picture of the frame that had the face
                                    img_name = f"{self.student_id}_{current_angle_idx}_{angle_captured}.jpg"
                                    img_path = os.path.join(student_dir, img_name)
                                    # Write the clean frame (without boxes drawn)
                                    cv2.imwrite(img_path, self.inference_frame)
                                    
                                    embeddings_list.append(embedding)
                                    angle_captured += 1
                                    captured_images += 1
                                    last_capture_time = curr_time
                                    
                    except Exception as e:
                        print(f"Error reading registration inference result: {e}")
                    
                    self.inference_future = None
                    self.inference_busy = False
                
                # Start background face detection if free
                if not self.inference_busy:
                    self.inference_busy = True
                    self.inference_frame = frame.copy() # Store the clean frame being evaluated
                    self.inference_future = self.executor.submit(self.run_inference, self.inference_frame)
                
                # Draw visual elements on the active frame at high frame rate
                if latest_bbox is not None:
                    cv2.rectangle(draw_frame, (latest_bbox[0], latest_bbox[1]), (latest_bbox[2], latest_bbox[3]), status_color, 2)
                    
                cv2.putText(draw_frame, f"{status_text} ({captured_images}/{total_images})", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2, cv2.LINE_AA)
                
                # Convert BGR frame to QImage and emit
                rgb_frame = cv2.cvtColor(draw_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                
                self.frame_ready.emit(qt_img)
                time.sleep(0.015) # Yield CPU (~60 FPS)
                
            if captured_images >= total_images:
                self.capture_finished.emit(True, "Face enrollment templates captured successfully!", embeddings_list)
            else:
                self.capture_finished.emit(False, "Capture session was cancelled or terminated.", [])
                
        except Exception as e:
            self.capture_finished.emit(False, f"Error in registration thread: {e}", [])
        finally:
            running_flag[0] = False
            threading.Thread(target=cap.release, daemon=True).start()
            if self.inference_future is not None:
                try:
                    self.inference_future.cancel()
                except Exception:
                    pass
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass

class RegisterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.preview_thread = None
        self.profile_image = None
        self.last_raw_frame = None
        self.init_ui()
        
    def init_ui(self):
        # Layout splits left inputs panel and right webcam screen
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Inputs)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        group_inputs = QGroupBox("👨‍🎓 Student Details")
        form_layout = QFormLayout(group_inputs)
        form_layout.setSpacing(12)
        
        self.txt_id = QLineEdit()
        self.txt_id.setReadOnly(True)
        self.txt_id.setStyleSheet("background-color: #1E293B; color: #94A3B8;")
        self.txt_id.setPlaceholderText("Auto-generated")
        form_layout.addRow("Student ID:", self.txt_id)
        
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Full Name")
        form_layout.addRow("Full Name:", self.txt_name)
        
        self.txt_roll = QLineEdit()
        self.txt_roll.setPlaceholderText("Roll Number")
        form_layout.addRow("Roll Number (Unique):", self.txt_roll)
        
        self.combo_class = QComboBox()
        self.combo_class.addItems([f"Class {i}" for i in range(1, 11)])
        form_layout.addRow("Class:", self.combo_class)
        
        self.combo_sec = QComboBox()
        self.combo_sec.addItems(["N/A", "A", "B", "C", "D", "E"])
        form_layout.addRow("Section:", self.combo_sec)
        
        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["Male", "Female", "Other"])
        form_layout.addRow("Gender:", self.combo_gender)
        
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Phone Number (Optional)")
        form_layout.addRow("Phone Number:", self.txt_phone)
        
        left_layout.addWidget(group_inputs)
        
        # Profile Photo Selection Box
        group_photo = QGroupBox("📸 Profile Photo Option")
        photo_layout = QVBoxLayout(group_photo)
        photo_layout.setSpacing(10)
        
        photo_row = QHBoxLayout()
        self.label_profile_preview = QLabel("No Photo")
        self.label_profile_preview.setFixedSize(80, 80)
        self.label_profile_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_profile_preview.setStyleSheet(
            "background-color: #0F172A; border: 2px dashed #1E293B; border-radius: 40px; color: #64748B; font-size: 10px;"
        )
        photo_row.addWidget(self.label_profile_preview)
        
        photo_btns = QVBoxLayout()
        self.btn_preview_cam = QPushButton("📷 Preview Camera")
        self.btn_preview_cam.setMinimumHeight(30)
        self.btn_preview_cam.clicked.connect(self.toggle_preview_camera)
        photo_btns.addWidget(self.btn_preview_cam)
        
        self.btn_snap_profile = QPushButton("📸 Capture Photo")
        self.btn_snap_profile.setMinimumHeight(30)
        self.btn_snap_profile.setEnabled(False)
        self.btn_snap_profile.clicked.connect(self.capture_profile_photo)
        photo_btns.addWidget(self.btn_snap_profile)
        
        photo_row.addLayout(photo_btns)
        photo_layout.addLayout(photo_row)
        left_layout.addWidget(group_photo)
        
        # Start button
        self.btn_start = QPushButton("🚀 Start Registration")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.clicked.connect(self.start_registration)
        left_layout.addWidget(self.btn_start)
        
        left_layout.addStretch()
        
        # Right Panel (Webcam Feed)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.label_feed = QLabel()
        self.label_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_feed.setMinimumSize(480, 360)
        self.label_feed.setStyleSheet("background-color: #0F172A; border: 2px dashed #1E293B; border-radius: 12px; color: #64748B;")
        self.label_feed.setText("Webcam Stream Placeholder\nFill forms and press 'Start Registration'")
        right_layout.addWidget(self.label_feed, 1)
        
        # Instruction Panel
        self.label_instruction = QLabel("🎯 Instructions: Adjust camera and look straight.")
        self.label_instruction.setStyleSheet("font-size: 13px; font-weight: bold; color: #818CF8; padding: 5px;")
        self.label_instruction.setWordWrap(True)
        right_layout.addWidget(self.label_instruction)
        
        self.label_angle = QLabel("Current Face Angle: None")
        self.label_angle.setStyleSheet("font-size: 12px; color: #94A3B8; padding: 2px;")
        right_layout.addWidget(self.label_angle)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, config.CAPTURE_COUNT)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Captures: %v/%m")
        right_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # Ensure recognizer is pre-initialized in background or first use
        recognizer.initialize()
        
    def generate_new_student_id(self) -> str:
        try:
            all_students = database.get_all_students()
            if not all_students:
                return "STU1001"
            max_num = 1000
            for s in all_students:
                sid = s["student_id"]
                if sid.startswith("STU") and sid[3:].isdigit():
                    num = int(sid[3:])
                    if num > max_num:
                        max_num = num
            return f"STU{max_num + 1}"
        except Exception:
            return "STU1001"

    def showEvent(self, event):
        self.txt_id.setText(self.generate_new_student_id())
        self.profile_image = None
        self.label_profile_preview.clear()
        self.label_profile_preview.setText("No Photo")
        event.accept()

    def toggle_preview_camera(self):
        if self.preview_thread and self.preview_thread.isRunning():
            self.stop_preview_camera()
        else:
            if self.thread and self.thread.isRunning():
                self.btn_preview_cam.setEnabled(False)
                try:
                    self.thread.capture_finished.disconnect()
                except Exception:
                    pass
                self.thread.finished.connect(self.start_preview_after_registration)
                self.thread.stop()
            else:
                self.start_preview_camera()

    def start_preview_camera(self):
        self.btn_preview_cam.setText("⏹️ Stop Preview")
        self.btn_preview_cam.setEnabled(True)
        self.btn_snap_profile.setEnabled(True)
        self.btn_start.setEnabled(False)
        
        self.preview_thread = PreviewThread()
        self.preview_thread.frame_ready.connect(self.update_preview_feed)
        self.preview_thread.finished.connect(self.on_preview_finished)
        self.preview_thread.start()

    def start_preview_after_registration(self):
        if self.thread:
            try:
                self.thread.finished.disconnect(self.start_preview_after_registration)
            except Exception:
                pass
            self.thread = None
        self.start_preview_camera()

    def stop_preview_camera(self):
        if self.preview_thread and self.preview_thread.isRunning():
            self.btn_preview_cam.setEnabled(False)
            self.preview_thread.stop()

    def on_preview_finished(self):
        self.btn_preview_cam.setText("📷 Preview Camera")
        self.btn_preview_cam.setEnabled(True)
        self.btn_snap_profile.setEnabled(False)
        self.btn_start.setEnabled(True)
        
        self.label_feed.clear()
        self.label_feed.setText("Webcam Stream Placeholder\nFill forms and press 'Start Registration'")
        self.preview_thread = None

    def update_preview_feed(self, image, raw_frame):
        self.last_raw_frame = raw_frame
        pixmap = QPixmap.fromImage(image)
        self.label_feed.setPixmap(pixmap.scaled(self.label_feed.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def capture_profile_photo(self):
        if self.last_raw_frame is not None:
            self.profile_image = self.last_raw_frame.copy()
            
            # Show a thumbnail preview in the circular label
            rgb_frame = cv2.cvtColor(self.profile_image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qt_img)
            
            self.label_profile_preview.setPixmap(
                pixmap.scaled(self.label_profile_preview.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            )
            self.stop_preview_camera()
            QMessageBox.information(self, "Profile Photo Captured", "Profile photo captured successfully! It will be saved when registration is completed.")

    def start_registration(self):
        # Valids
        student_id = self.txt_id.text().strip()
        name = self.txt_name.text().strip()
        roll = self.txt_roll.text().strip()
        class_name = self.combo_class.currentText()
        section = self.combo_sec.currentText()
        gender = self.combo_gender.currentText()
        phone = self.txt_phone.text().strip()
        
        if not student_id or not name or not roll:
            QMessageBox.warning(self, "Validation Error", "Please fill Student ID, Full Name, and Roll Number.")
            return
            
        # Check SQLite ID
        db_student = database.get_student(student_id)
        if db_student:
            QMessageBox.warning(self, "Duplicate Error", f"Student ID '{student_id}' is already registered under {db_student['name']}.")
            return
            
        # Check SQLite Roll Number
        all_students = database.get_all_students()
        for s in all_students:
            if s["roll_number"] == roll and s["class_name"] == class_name and s["section"] == section:
                QMessageBox.warning(self, "Duplicate Error", f"Roll Number '{roll}' is already taken in {class_name} Section {section} by {s['name']}.")
                return
                
        # Lock buttons
        self.btn_start.setEnabled(False)
        self.btn_preview_cam.setEnabled(False)
        self.btn_snap_profile.setEnabled(False)
        self.txt_name.setEnabled(False)
        self.txt_roll.setEnabled(False)
        self.combo_class.setEnabled(False)
        self.combo_sec.setEnabled(False)
        self.combo_gender.setEnabled(False)
        self.txt_phone.setEnabled(False)
        
        # Stop preview camera before opening it in the registration thread
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.finished.connect(lambda: self.start_registration_thread(student_id, name, roll, class_name, section, gender, phone))
            self.preview_thread.stop()
        else:
            self.start_registration_thread(student_id, name, roll, class_name, section, gender, phone)

    def start_registration_thread(self, student_id, name, roll, class_name, section, gender, phone):
        if self.preview_thread:
            try:
                self.preview_thread.finished.disconnect()
            except Exception:
                pass
            self.preview_thread = None
            
        # Setup and start Thread
        self.thread = RegisterThread(student_id)
        self.thread.frame_ready.connect(self.update_feed)
        self.thread.progress_updated.connect(self.update_progress)
        self.thread.capture_finished.connect(lambda s, m, e: self.on_capture_finished(s, m, e, student_id, name, roll, class_name, section, gender, phone))
        self.thread.finished.connect(self.on_registration_thread_finished)
        
        self.progress_bar.setValue(0)
        self.thread.start()

    def on_registration_thread_finished(self):
        if self.thread:
            try:
                self.thread.finished.disconnect(self.on_registration_thread_finished)
            except Exception:
                pass
            self.thread = None
        
    def update_feed(self, image):
        pixmap = QPixmap.fromImage(image)
        # Scaled fitting label preserving aspect ratio
        self.label_feed.setPixmap(pixmap.scaled(self.label_feed.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
    def update_progress(self, count, angle, instruction):
        self.progress_bar.setValue(count)
        self.label_angle.setText(f"Current Face Angle: <b>{angle}</b>")
        self.label_instruction.setText(f"🎯 Instruction: {instruction}")
        
    def on_capture_finished(self, success, message, embeddings, student_id, name, roll, class_name, section, gender, phone):
        # Enable controls back
        self.btn_start.setEnabled(True)
        self.btn_preview_cam.setEnabled(True)
        self.txt_name.setEnabled(True)
        self.txt_roll.setEnabled(True)
        self.combo_class.setEnabled(True)
        self.combo_sec.setEnabled(True)
        self.combo_gender.setEnabled(True)
        self.txt_phone.setEnabled(True)
        
        # Release pixmap
        self.label_feed.clear()
        self.label_feed.setText("Webcam Stream Placeholder\nFill forms and press 'Start Registration'")
        self.label_angle.setText("Current Face Angle: None")
        self.label_instruction.setText("🎯 Instructions: Adjust camera and look straight.")
        
        if success and len(embeddings) >= 15:
            # Commit to SQLite
            db_success = database.add_student(
                student_id=student_id,
                name=name,
                roll_number=roll,
                class_name=class_name,
                section=section,
                gender=gender,
                phone=phone if phone else None
            )
            
            if db_success:
                # Add to pickle file
                encodings = load_all_encodings()
                encodings[student_id] = embeddings
                save_all_encodings(encodings)
                
                # Re-init recognizer singleton database cache
                recognizer.load_encodings_cache()
                
                # Save Profile Picture
                student_dir = os.path.join(config.DATASET_DIR, student_id)
                os.makedirs(student_dir, exist_ok=True)
                
                if self.profile_image is not None:
                    profile_path = os.path.join(student_dir, "profile.jpg")
                    cv2.imwrite(profile_path, self.profile_image)
                else:
                    first_img_name = f"{student_id}_0_0.jpg"
                    first_img_path = os.path.join(student_dir, first_img_name)
                    if os.path.exists(first_img_path):
                        img = cv2.imread(first_img_path)
                        cv2.imwrite(os.path.join(student_dir, "profile.jpg"), img)
                        
                QMessageBox.information(self, "Enrollment Success", f"🎉 Student '{name}' registered and trained successfully with {len(embeddings)} template vectors!")
                
                # Clear fields
                self.txt_id.setText(self.generate_new_student_id())
                self.txt_name.clear()
                self.txt_roll.clear()
                self.txt_phone.clear()
                self.progress_bar.setValue(0)
                self.profile_image = None
                self.label_profile_preview.clear()
                self.label_profile_preview.setText("No Photo")
            else:
                QMessageBox.critical(self, "Database Error", "Failed to register student details in SQLite database.")
        else:
            QMessageBox.critical(self, "Registration Failed", f"Enrollment session failed. {message}")
            
    def stop_session(self, silent=False):
        if self.preview_thread and self.preview_thread.isRunning():
            if silent:
                try:
                    self.preview_thread.frame_ready.disconnect()
                    self.preview_thread.finished.disconnect()
                except (TypeError, RuntimeError):
                    pass
            self.preview_thread.stop()
            
        if self.thread and self.thread.isRunning():
            if silent:
                try:
                    self.thread.frame_ready.disconnect()
                    self.thread.progress_updated.disconnect()
                    self.thread.capture_finished.disconnect()
                    self.thread.finished.disconnect()
                except (TypeError, RuntimeError):
                    pass
            self.thread.stop()
            
        if silent:
            # Enable controls back
            self.btn_start.setEnabled(True)
            self.btn_preview_cam.setEnabled(True)
            self.txt_name.setEnabled(True)
            self.txt_roll.setEnabled(True)
            self.combo_class.setEnabled(True)
            self.combo_sec.setEnabled(True)
            self.combo_gender.setEnabled(True)
            self.txt_phone.setEnabled(True)
            
            # Reset UI visuals
            self.label_feed.clear()
            self.label_feed.setText("Webcam Stream Placeholder\nFill forms and press 'Start Registration'")
            self.label_angle.setText("Current Face Angle: None")
            self.label_instruction.setText("🎯 Instructions: Adjust camera and look straight.")
            self.progress_bar.setValue(0)
            self.profile_image = None
            self.label_profile_preview.clear()
            self.label_profile_preview.setText("No Photo")
            self.preview_thread = None
            self.thread = None

    def closeEvent(self, event):
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.stop()
            self.preview_thread.wait(500)
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait(500)
        event.accept()
