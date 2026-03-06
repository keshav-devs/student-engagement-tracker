import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time
from collections import deque
from db_service import log_engagement

# Initialize the new Tasks API FaceLandmarker
base_options = python.BaseOptions(model_asset_path='face_landmarker_v2_with_blendshapes.task')
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=20, # Increased from 10 to 20
    min_face_detection_confidence=0.5, # Changed to 0.5
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5 # Changed to 0.5
)
face_landmarker = vision.FaceLandmarker.create_from_options(options)

# Constants for smoothing
SMOOTHING_WINDOW_SECONDS = 5
FPS_ESTIMATE = 10 # approximate fps
HISTORY_LENGTH = SMOOTHING_WINDOW_SECONDS * FPS_ESTIMATE
# History only used for DB logging (not for displayed score)
engagement_history = deque(maxlen=HISTORY_LENGTH)

last_db_log_time = time.time()
LOGGING_INTERVAL = 30 # seconds

# Grace Period: track when each face index was last seen as engaged
# If lost for < 1 second, don't trigger distraction (handles blinks)
GRACE_PERIOD = 1.0  # seconds
last_engaged_time = {}  # face_index -> timestamp
def estimate_yaw_angle(face_landmarks, frame_w, frame_h):
    """Estimates head yaw angle (in degrees) from nose-to-face-edge distance ratio.
    Returns: yaw_angle (float, 0=centered, positive=turned), nose_px (tuple), vector_end (tuple)"""
    
    # Nose tip position
    nose_x = face_landmarks[1].x * frame_w
    nose_y = face_landmarks[1].y * frame_h
    
    # Face edges from landmarks
    all_x = [lm.x * frame_w for lm in face_landmarks]
    face_left = min(all_x)
    face_right = max(all_x)
    face_width = face_right - face_left
    
    if face_width <= 0:
        return 0.0, (int(nose_x), int(nose_y)), (int(nose_x), int(nose_y))
    
    # Distance from nose to each edge
    dist_left = nose_x - face_left
    dist_right = face_right - nose_x
    
    # Yaw ratio: 0.5 = perfectly centered, 0.0 or 1.0 = fully turned
    nose_ratio = dist_left / face_width  # 0.0 = nose at left edge, 1.0 = nose at right edge
    
    # Convert to yaw deviation: 0.0 = centered, 0.5 = fully turned to one side
    yaw_deviation = abs(nose_ratio - 0.5)
    
    # Map deviation to approximate angle (0-45 degrees)
    # deviation 0.0 = 0°, deviation 0.5 = 45°
    yaw_angle = yaw_deviation * 90.0  # Scale: 0° to 45° maps to deviation 0 to 0.5
    
    # Focus Vector: direction the nose is "pointing"
    # Centered nose -> vector points straight at camera (downward in image = toward viewer)
    # Turned nose -> vector angles sideways
    vector_length = 60
    # yaw_direction: negative = turned left, positive = turned right
    yaw_direction = (nose_ratio - 0.5) * 2.0  # -1.0 to 1.0
    vector_dx = int(yaw_direction * vector_length)
    vector_dy = int((1.0 - abs(yaw_direction)) * vector_length * 0.5)  # Shorter when turned
    
    nose_px = (int(nose_x), int(nose_y))
    vector_end = (int(nose_x) + vector_dx, int(nose_y) + vector_dy)
    
    return yaw_angle, nose_px, vector_end

def get_engagement_score(face_landmarks, frame_w, frame_h):
    """Returns continuous engagement score 0.0-100.0 using linear interpolation.
    No hard cutoffs, no rounding — pure float values.
    0° yaw = 100%, 45° yaw = 0%, smooth linear transition."""
    
    yaw_angle, nose_px, vector_end = estimate_yaw_angle(face_landmarks, frame_w, frame_h)
    
    # Linear interpolation: engagement = 100 - (yaw_angle * factor)
    # At 0° -> 100%, at 45° -> 0%
    factor = 100.0 / 45.0  # ~2.222 per degree
    engagement = 100.0 - (yaw_angle * factor)
    
    # Clamp to valid range (no rounding!)
    engagement = max(0.0, min(100.0, engagement))
    
    return engagement, yaw_angle, nose_px, vector_end

def get_bounding_box(face_landmarks, frame_w, frame_h):
    x_min = min([landmark.x for landmark in face_landmarks])
    x_max = max([landmark.x for landmark in face_landmarks])
    y_min = min([landmark.y for landmark in face_landmarks])
    y_max = max([landmark.y for landmark in face_landmarks])
    
    return int(x_min * frame_w), int(y_min * frame_h), int(x_max * frame_w), int(y_max * frame_h)

def process_frame(frame, show_landmarks=False):
    global last_db_log_time, engagement_history
    
    frame_h, frame_w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    results = face_landmarker.detect(mp_image)
    
    students_total = 0
    score_sum = 0.0
    
    if len(results.face_landmarks) > 0:
        students_total = len(results.face_landmarks)
        
        for face_idx, face_landmarks in enumerate(results.face_landmarks):
            x1, y1, x2, y2 = get_bounding_box(face_landmarks, frame_w, frame_h)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame_w, x2), min(frame_h, y2)
            
            engagement, yaw_angle, nose_px, vector_end = get_engagement_score(
                face_landmarks, frame_w, frame_h
            )
            
            score_sum += engagement
            
            # Color based on continuous score (no hard cutoff)
            if engagement >= 50.0:
                # Green intensity scales with engagement
                g_intensity = int(155 + (engagement / 100.0) * 100)
                color = (0, min(255, g_intensity), 0)
                label = f"Engaged ({engagement:.1f}%)"
            else:
                # Red intensity scales with distraction
                r_intensity = int(155 + ((100 - engagement) / 100.0) * 100)
                color = (0, 0, min(255, r_intensity))
                label = f"Distracted ({engagement:.1f}%)"
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # === Focus Vector: always drawn ===
            # Green when engaged, red when distracted, length shows confidence
            vec_color = (0, 255, 0) if engagement >= 50 else (0, 0, 255)
            cv2.arrowedLine(frame, nose_px, vector_end, vec_color, 2, tipLength=0.3)
            
            # === Debug Overlay (when toggled) ===
            if show_landmarks:
                # Iris center (cyan)
                iris_x = int(face_landmarks[468].x * frame_w)
                iris_y = int(face_landmarks[468].y * frame_h)
                cv2.circle(frame, (iris_x, iris_y), 4, (255, 255, 0), -1)
                
                # Eye corners (yellow)
                for lm_idx in [33, 133, 263, 362]:
                    px = int(face_landmarks[lm_idx].x * frame_w)
                    py = int(face_landmarks[lm_idx].y * frame_h)
                    cv2.circle(frame, (px, py), 3, (0, 255, 255), -1)
                
                # Face edges (magenta)
                cv2.line(frame, (x1, y1), (x1, y2), (255, 0, 255), 2)
                cv2.line(frame, (x2, y1), (x2, y2), (255, 0, 255), 2)
                
                # Yaw angle text
                cv2.putText(frame, f"Yaw: {yaw_angle:.1f} deg", (x1, y2 + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # CEI = average engagement score across all faces (raw float, no rounding)
    cei_raw = (score_sum / students_total) if students_total > 0 else 0.0
    
    engagement_history.append(cei_raw)
    cei_for_db = sum(engagement_history) / len(engagement_history) if len(engagement_history) > 0 else 0
    
    current_time = time.time()
    if current_time - last_db_log_time >= LOGGING_INTERVAL:
        log_engagement(students_total, cei_for_db)
        last_db_log_time = current_time
        
    return frame, students_total, cei_raw

def release_resources():
    face_landmarker.close()
