# 🤖 AutoAttend AI: Desktop Face Recognition Attendance Management System

A standalone, native offline **PyQt6 Desktop Application** for schools, colleges, and workplaces. This system leverages the state-of-the-art **InsightFace** engine featuring **RetinaFace** for face detection, **ArcFace** for extracting 512-dimensional face embeddings, and vectorized **Cosine Similarity** for real-time identification.

Built with a modern, glassmorphic dark-theme desktop window and integrated **Matplotlib** graphics, the panel allows enrollment of student profiles, captures multi-angle face pictures, prevents duplicate attendance logs, displays live webcam identification, provides data visualization charts, and manages databases completely offline.

---

## 🌟 Key Features

1. **Standalone Offline GUI**: Native desktop interface (PyQt6) that runs locally on your PC without hosting a server or opening browser tabs.
2. **Smooth Multi-Threaded Camera Streams**: Runs camera frame capture and face matching in background workers (`QThread`), keeping the user interface completely responsive and lag-free.
3. **Guided Multi-Angle Registration**: Step-by-step camera enrollment (Front, Left, Right, Up, Down, Smile, Neutral) capturing 35 templates to build a facial representation on disk and in an embedding database (`encodings_arcface.pkl`).
4. **Real-Time Webcam Identification**: High-performance multi-face check-in stream drawing styled boxes overlaying names, IDs, and cosine similarities. Unknown faces are rejected and labeled `UNKNOWN`.
5. **Double Logging Verification**: Logs attendance concurrently in a local SQLite file (`attendance.db`) and auto-generated daily CSV sheets (`attendance/YYYY-MM-DD.csv`).
6. **Duplicate Prevention**: Debounces and tracks live session check-ins to prevent multiple logs for a single student on the same day.
7. **Offline Analytics**: Clean dashboard displaying total counts, attendance rates, class distributions, weekly/monthly check-in trends, top attendees, and recent activity logs using Matplotlib charts.
8. **Detailed Record History**: Search by date ranges, classes, sections, names, and IDs, with export options to CSV or Excel sheet and log deletions.
9. **Dataset Browser & Profile CRUD**: Browse the student list, view individual profile details with a grid view of all 35 captured angles, update credentials, or delete students completely (wipes files, SQLite entries, and pickles).
10. **Configurable settings**: Adjust similarity thresholds, camera inputs, stream resolutions, folder locations, template counts, and UI themes (Dark/Light).

---

## 🛠️ Technology Stack

* **Python 3.11+**
* **PyQt6** (Desktop GUI Framework)
* **Matplotlib** (Embedded analytics graphing)
* **OpenCV** (Video capture & frames handling)
* **InsightFace** (RetinaFace for face detection + ArcFace for face recognition)
* **ONNX Runtime** (Optimized CPU/GPU inference)
* **SQLite** (Student profiles and log storage)
* **Pandas** (Data manipulation)
* **Pickle** (Binary database of face encodings)
* **Pillow** (Image loading)
* **OpenPyXL** (Excel spreadsheet compiler)

---

## 📂 Project Directory Structure

```text
Attendance/
├── app.py                  # Main PyQt6 GUI entrypoint, QSS styles, page navigation
├── config.py               # Path constants & dynamic configurations
├── database.py             # SQLite helper and DB CRUD query pipelines
├── utils.py                # Vectorized ArcFace matching engine and file exporters
├── register.py             # Student enrollment and angle capture widget (QThread camera)
├── recognize.py            # Live webcam attendance capture widget (QThread recognizer)
├── dashboard.py            # Matplotlib analytics & metrics cards widget
├── attendance_history.py   # Historical log browser, CSV/Excel exporter dialogs
├── student_management.py   # Student database browser, profile edits, & thumbnail gallery
├── settings.py             # Settings widget (thresholds, resolutions, camera inputs)
├── requirements.txt        # PIP dependencies list
├── README.md               # User manual
├── dataset/                # Folder storing captured student face images [Auto-created]
├── attendance/             # Folder containing daily CSV log reports [Auto-created]
├── models/                 # Location where local InsightFace models are loaded [Auto-created]
└── encodings_arcface.pkl   # Binary database cache of registered embeddings [Auto-created]
```

---

## ⚙️ Installation & Setup

### 1. Place Files in Project Folder
Move all project files directly to your workspace folder:
```text
c:\Users\PGHS\StudioProjects\Attendance
```

### 2. Install Python Dependencies
Open your terminal and install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Connect Camera Hardware
Ensure your webcam is connected to the system. The application defaults to camera index `0`. You can change this index directly in the system settings panel.

### 4. Running the Application
Launch the PyQt6 application:
```bash
python app.py
```
This opens the standalone desktop admin dashboard directly on your screen.

*Note: On first startup, InsightFace will download the `buffalo_l` ONNX model files to your local `models/` directory. This initial step requires an active internet connection.*

---

## 🧪 Pipeline Unit Tests

To run the automated verification suite to test database operations, configs, and matching mathematical models:
```bash
python scratch/test_pipeline.py
```
