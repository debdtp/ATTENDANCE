from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
                             QSplitter, QSlider, QFormLayout, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import time
from datetime import datetime
import queue
import threading

import database
from utils import recognizer, append_to_daily_csv, _open_camera_with_retry
import config
from concurrent.futures import ThreadPoolExecutor

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

class RecognizeThread(QThread):
    frame_ready = pyqtSignal(QImage)
    attendance_logged = pyqtSignal(str, str, str, str, str, str) # student_id, name, class_name, section, time, confidence
    
    def __init__(self, threshold):
        super().__init__()
        self.threshold = threshold
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.inference_future = None
        self.inference_busy = False
        self.latest_results = []
        
    def stop(self):
        self.running = False
        
    def update_threshold(self, threshold):
        self.threshold = threshold
        
    def run_inference(self, frame_copy):
        try:
            return recognizer.extract_faces(frame_copy)
        except Exception as e:
            print(f"Error in background inference: {e}")
            return []
            
    def run(self):
        import smartboard_server
        smartboard_server.notify_session_status(True)
        
        cap = _open_camera_with_retry(config.CAMERA_INDEX)
        if cap is None:
            smartboard_server.notify_session_status(False)
            return
            
        # Parse resolution
        width, height = 640, 480
        if config.CAMERA_RESOLUTION == "1280x720":
            width, height = 1280, 720
        elif config.CAMERA_RESOLUTION == "1920x1080":
            width, height = 1920, 1080
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Student Cache
        student_cache = {s["student_id"]: s for s in database.get_all_students()}
        
        # Debounce timer for unknown face logging
        last_unknown_log_time = 0
        prev_time = 0
        
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
                except queue.Empty:
                    continue
                    
                frame = cv2.flip(frame, 1)
                
                # FPS
                curr_time = time.time()
                fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0.0
                prev_time = curr_time
                
                # Check background inference future status
                if self.inference_future is not None and self.inference_future.done():
                    try:
                        faces = self.inference_future.result()
                        # Process results to extract student matches
                        new_results = []
                        for face in faces:
                            bbox = face["bbox"]
                            embedding = face["normed_embedding"]
                            if embedding is None:
                                continue
                                
                            student_id, similarity = recognizer.match_face(embedding, self.threshold)
                            
                            box_color = (0, 0, 255) # Default Red
                            text_lines = []
                            
                            if student_id and student_id in student_cache:
                                student = student_cache[student_id]
                                name = student["name"]
                                class_name = student["class_name"]
                                section = student["section"]
                                confidence_pct = similarity * 100
                                
                                box_color = (0, 255, 0) # Green
                                text_lines = [
                                    name,
                                    f"ID: {student_id}",
                                    f"Confidence: {confidence_pct:.1f}%"
                                ]
                                
                                # SQLite Log
                                marked = database.mark_attendance(
                                    student_id=student_id,
                                    name=name,
                                    class_name=class_name,
                                    section=section,
                                    confidence=similarity
                                )
                                
                                if marked:
                                    # CSV Append
                                    append_to_daily_csv(
                                        student_id=student_id,
                                        name=name,
                                        class_name=class_name,
                                        section=section,
                                        confidence=similarity
                                    )
                                    # Emit back to GUI table
                                    now_time_str = datetime.now().strftime("%H:%M:%S")
                                    self.attendance_logged.emit(
                                        student_id, name, class_name, section, now_time_str, f"{confidence_pct:.1f}%"
                                    )
                                    # Broadcast attendance to Smartboard
                                    smartboard_server.notify_attendance(
                                        student_id=student_id,
                                        name=name,
                                        class_name=class_name,
                                        section=section,
                                        time_str=now_time_str,
                                        confidence_pct=f"{confidence_pct:.1f}%"
                                    )
                                    # Speak name present offline via PowerShell (runs in background)
                                    try:
                                        import subprocess
                                        cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{name} present')"
                                        subprocess.Popen(["powershell", "-Command", cmd], creationflags=0x08000000)
                                    except Exception as e:
                                        print(f"Error calling desktop TTS: {e}")
                            else:
                                similarity_pct = similarity * 100 if similarity > 0 else 0.0
                                box_color = (0, 0, 255) # Red
                                text_lines = [
                                    "UNKNOWN",
                                    "ID: N/A",
                                    f"Similarity: {similarity_pct:.1f}%"
                                ]
                                
                                # Debounced unknown logging (every 3 seconds)
                                curr_ts = time.time()
                                if curr_ts - last_unknown_log_time > 3.0:
                                    database.log_unknown_detection(similarity)
                                    last_unknown_log_time = curr_ts
                                    
                            new_results.append({
                                "bbox": bbox,
                                "box_color": box_color,
                                "text_lines": text_lines
                            })
                        self.latest_results = new_results
                    except Exception as e:
                        print(f"Error reading inference result: {e}")
                    self.inference_future = None
                    self.inference_busy = False
 
                # If background worker is free, feed it a copy of the latest frame
                if not self.inference_busy:
                    self.inference_busy = True
                    self.inference_future = self.executor.submit(self.run_inference, frame.copy())
                
                # Draw the latest known results on the active frame (extremely smooth!)
                for res in self.latest_results:
                    bbox = res["bbox"]
                    box_color = res["box_color"]
                    text_lines = res["text_lines"]
                    
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), box_color, 2)
                    y_offset = bbox[1] - 10
                    for line in reversed(text_lines):
                        cv2.putText(frame, line, (bbox[0], y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 1, cv2.LINE_AA)
                        y_offset -= 18
                        
                cv2.putText(frame, f"FPS: {fps:.1f}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
                
                # Broadcast the live frame to the Smartboard
                smartboard_server.notify_frame(frame, fps)
                
                # Convert frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                
                self.frame_ready.emit(qt_img)
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Error in recognition thread: {e}")
        finally:
            running_flag[0] = False
            threading.Thread(target=cap.release, daemon=True).start()
            smartboard_server.notify_session_status(False)
            # Clean up and wait for background execution to complete
            if self.inference_future is not None:
                try:
                    self.inference_future.cancel()
                except Exception:
                    pass
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass

class RecognizeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Webcam & Controls)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        self.label_feed = QLabel()
        self.label_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_feed.setMinimumSize(480, 360)
        self.label_feed.setStyleSheet("background-color: #0F172A; border: 2px dashed #1E293B; border-radius: 12px; color: #64748B;")
        self.label_feed.setText("Webcam Stream Placeholder\nPress 'Start Attendance Session' to begin.")
        left_layout.addWidget(self.label_feed, 1)
        
        # Configuration Slider Box
        group_controls = QGroupBox("⚙️ Live Settings")
        control_layout = QFormLayout(group_controls)
        
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setMinimum(30)
        self.slider_thresh.setMaximum(100)
        self.slider_thresh.setValue(int(float(config.RECOGNITION_THRESHOLD) * 100))
        self.slider_thresh.valueChanged.connect(self.on_threshold_changed)
        
        self.label_thresh = QLabel(f"{self.slider_thresh.value() / 100:.2f}")
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(self.slider_thresh)
        thresh_layout.addWidget(self.label_thresh)
        
        control_layout.addRow("Cosine Threshold:", thresh_layout)
        left_layout.addWidget(group_controls)
        
        # Start/Stop Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Start Session")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_session)
        
        self.btn_stop = QPushButton("⏹️ Stop Session")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_session)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        left_layout.addLayout(btn_layout)
        
        # Right Panel (Logged Attendance Table)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_layout.addWidget(QLabel("📝 Marked Present in Current Running Session:"))
        
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(6)
        self.table_logs.setHorizontalHeaderLabels(["Time", "Student ID", "Name", "Class", "Section", "Confidence"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_logs.setStyleSheet("background-color: #1E293B; color: #F8FAFC; gridline-color: #334155;")
        self.table_logs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_logs.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table_logs)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        
        layout.addWidget(splitter)
        
        # Pre-initialize in background
        recognizer.initialize()
        
    def start_session(self):
        # Verify student profiles exist
        students = database.get_all_students()
        if not students:
            QMessageBox.warning(self, "No Students", "There are no registered students in the database. Please enroll students first.")
            return
            
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.table_logs.setRowCount(0)
        
        self.thread = RecognizeThread(self.slider_thresh.value() / 100)
        self.thread.frame_ready.connect(self.update_feed)
        self.thread.attendance_logged.connect(self.add_log_row)
        self.thread.finished.connect(self.on_session_finished)
        self.thread.start()
        
    def stop_session(self):
        if self.thread and self.thread.isRunning():
            self.btn_stop.setEnabled(False)
            self.label_feed.setText("Stopping attendance session...")
            self.thread.stop()
            
    def on_session_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        
        self.label_feed.clear()
        self.label_feed.setText("Webcam Stream Placeholder\nPress 'Start Attendance Session' to begin.")
        if self.thread:
            try:
                self.thread.finished.disconnect(self.on_session_finished)
            except Exception:
                pass
            self.thread = None
        
    def update_feed(self, image):
        pixmap = QPixmap.fromImage(image)
        self.label_feed.setPixmap(pixmap.scaled(self.label_feed.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
    def on_threshold_changed(self, val):
        thresh = val / 100
        self.label_thresh.setText(f"{thresh:.2f}")
        if self.thread and self.thread.isRunning():
            self.thread.update_threshold(thresh)
            
    def add_log_row(self, student_id, name, class_name, section, log_time, confidence):
        row_count = self.table_logs.rowCount()
        self.table_logs.insertRow(row_count)
        
        self.table_logs.setItem(row_count, 0, QTableWidgetItem(log_time))
        self.table_logs.setItem(row_count, 1, QTableWidgetItem(student_id))
        self.table_logs.setItem(row_count, 2, QTableWidgetItem(name))
        self.table_logs.setItem(row_count, 3, QTableWidgetItem(class_name))
        self.table_logs.setItem(row_count, 4, QTableWidgetItem(section))
        self.table_logs.setItem(row_count, 5, QTableWidgetItem(confidence))
        
        # Auto scroll to bottom
        self.table_logs.scrollToBottom()
        
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait(500)
        event.accept()
