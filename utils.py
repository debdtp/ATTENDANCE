import os
import pickle
import numpy as np
import cv2
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional, Any
import urllib.request
import queue
import threading
import time

from insightface.app import FaceAnalysis
from config import ENCODINGS_PATH, MODELS_DIR, ATTENDANCE_DIR

logger = logging.getLogger(__name__)

class IPCameraVideoCapture:
    def __init__(self, url):
        self.url = url
        self.stream = None
        self.bytes_buffer = b''
        self.is_opened = False
        self.open()
        
    def open(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            self.stream = urllib.request.urlopen(req, timeout=3.0)
            self.is_opened = True
        except Exception as e:
            logger.error(f"Error opening IP camera stream: {e}")
            self.is_opened = False
            
    def isOpened(self):
        return self.is_opened
        
    def read(self):
        if not self.is_opened or self.stream is None:
            return False, None
            
        try:
            while True:
                chunk = self.stream.read(4096)
                if not chunk:
                    return False, None
                self.bytes_buffer += chunk
                
                a = self.bytes_buffer.find(b'\xff\xd8')
                b = self.bytes_buffer.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    if a < b:
                        jpg = self.bytes_buffer[a:b+2]
                        self.bytes_buffer = self.bytes_buffer[b+2:]
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return True, frame
                    else:
                        self.bytes_buffer = self.bytes_buffer[a:]
        except Exception as e:
            logger.error(f"Error reading from IP camera stream: {e}")
            return False, None
            
    def release(self):
        self.is_opened = False
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.bytes_buffer = b''
        
    def set(self, propId, value):
        return True

def _open_camera_with_retry(index, retries=5, delay=0.2):
    is_ip_camera = False
    if isinstance(index, str) and (index.startswith("http://") or index.startswith("https://")):
        is_ip_camera = True
        
    for i in range(retries):
        if is_ip_camera:
            cap = IPCameraVideoCapture(index)
        else:
            try:
                cam_idx = int(index)
            except (ValueError, TypeError):
                cam_idx = index
            cap = cv2.VideoCapture(cam_idx)
            
        if cap.isOpened():
            return cap
            
        cap.release()
        time.sleep(delay)
    return None

class FaceRecognizer:
    def __init__(self):
        self.app = None
        self.known_embeddings: Optional[np.ndarray] = None  # Shape: (N, 512)
        self.known_ids: List[str] = []                       # Length: N
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initializes the InsightFace model."""
        if self.initialized:
            return True
        try:
            logger.info("Initializing InsightFace model...")
            # Initialize RetinaFace and ArcFace modules. Disable gender/age estimation for performance.
            self.app = FaceAnalysis(name='buffalo_l', root=MODELS_DIR, allowed_modules=['detection', 'recognition'])
            # Prepare face detector with optimized detection size
            self.app.prepare(ctx_id=-1, det_size=(320, 320))
            self.initialized = True
            logger.info("InsightFace model initialized successfully.")
            self.load_encodings_cache()
            return True
        except Exception as e:
            logger.error(f"Error initializing FaceRecognizer: {e}")
            return False

    def load_encodings_cache(self) -> None:
        """Loads and vectorizes the pickle database cache of embeddings."""
        if not os.path.exists(ENCODINGS_PATH):
            self.known_embeddings = None
            self.known_ids = []
            logger.info("No face encodings pickle file found. Cache is empty.")
            return

        try:
            with open(ENCODINGS_PATH, "rb") as f:
                encodings_dict: Dict[str, List[np.ndarray]] = pickle.load(f)
            
            embeddings_list = []
            ids_list = []
            
            for student_id, embs in encodings_dict.items():
                for emb in embs:
                    # Ensure embedding is unit-normalized for direct dot-product cosine similarity
                    norm = np.linalg.norm(emb)
                    normed_emb = emb / norm if norm > 0 else emb
                    embeddings_list.append(normed_emb)
                    ids_list.append(student_id)
            
            if embeddings_list:
                self.known_embeddings = np.vstack(embeddings_list)
                self.known_ids = ids_list
                logger.info(f"Loaded {self.known_embeddings.shape[0]} embeddings representing {len(encodings_dict)} students.")
            else:
                self.known_embeddings = None
                self.known_ids = []
        except Exception as e:
            logger.error(f"Error loading encodings cache: {e}")
            self.known_embeddings = None
            self.known_ids = []

    def extract_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces, aligns them, and generates embeddings.
        Returns:
            List of dicts containing bbox, kps, and normalized embedding.
        """
        if not self.initialized:
            raise RuntimeError("FaceRecognizer is not initialized. Call initialize() first.")
            
        try:
            # OpenCV captures BGR, InsightFace expects RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = self.app.get(rgb_frame)
            
            results = []
            for face in faces:
                bbox = face.bbox.astype(int)
                kps = face.kps
                embedding = face.embedding
                
                if embedding is not None:
                    # L2 Normalize the embedding vector
                    norm = np.linalg.norm(embedding)
                    normed_emb = embedding / norm if norm > 0 else embedding
                else:
                    normed_emb = None
                    
                results.append({
                    "bbox": bbox,       # [x1, y1, x2, y2]
                    "kps": kps,         # 5 facial landmark keypoints
                    "embedding": embedding,
                    "normed_embedding": normed_emb
                })
            return results
        except Exception as e:
            logger.error(f"Error extracting faces: {e}")
            return []

    def match_face(self, normed_embedding: np.ndarray, threshold: float) -> Tuple[Optional[str], float]:
        """
        Compares an input embedding against the database cache.
        Returns:
            Tuple: (Matched Student ID or None, Similarity score)
        """
        if self.known_embeddings is None or len(self.known_ids) == 0:
            return None, 0.0
            
        try:
            # Cosine similarity is the dot product of normalized embeddings
            similarities = np.dot(self.known_embeddings, normed_embedding)
            max_idx = np.argmax(similarities)
            best_similarity = float(similarities[max_idx])
            
            if best_similarity >= threshold:
                return self.known_ids[max_idx], best_similarity
            else:
                return None, best_similarity
        except Exception as e:
            logger.error(f"Error matching face: {e}")
            return None, 0.0

def load_all_encodings() -> Dict[str, List[np.ndarray]]:
    """Loads all student encodings from pickle file."""
    if os.path.exists(ENCODINGS_PATH):
        try:
            with open(ENCODINGS_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading pickle encodings: {e}")
            return {}
    return {}

def save_all_encodings(encodings: Dict[str, List[np.ndarray]]) -> bool:
    """Saves all student encodings to pickle file."""
    try:
        with open(ENCODINGS_PATH, "wb") as f:
            pickle.dump(encodings, f)
        return True
    except Exception as e:
        logger.error(f"Error saving pickle encodings: {e}")
        return False

def append_to_daily_csv(student_id: str, name: str, class_name: str, section: str, confidence: float, status: str = "Present") -> None:
    """Appends an attendance record to the daily CSV file."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    file_path = os.path.join(ATTENDANCE_DIR, f"{date_str}.csv")
    new_record = {
        "Date": date_str,
        "Time": time_str,
        "Student ID": student_id,
        "Student Name": name,
        "Class": class_name,
        "Section": section,
        "Status": status,
        "Confidence": f"{confidence * 100:.1f}%"
    }
    
    try:
        # Check if record exists for this student today
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Avoid duplicate logs for the same student on the same day
            if student_id in df["Student ID"].astype(str).values:
                return
            df_new = pd.DataFrame([new_record])
            df_new.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df_new = pd.DataFrame([new_record])
            df_new.to_csv(file_path, index=False)
        logger.info(f"Appended attendance for {name} to {file_path}")
    except Exception as e:
        logger.error(f"Error appending attendance to CSV: {e}")

# Global instance of FaceRecognizer (singleton pattern)
recognizer = FaceRecognizer()
