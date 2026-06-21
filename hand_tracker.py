import cv2
import mediapipe as mp
import threading
import math
import time

class HandTracker:
    def __init__(self, camera_index=0, detection_confidence=0.7, tracking_confidence=0.7):
        self.camera_index = camera_index
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = None
        
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # State variables (thread-safe access)
        self.index_coords = None     # (x, y)
        self.thumb_coords = None     # (x, y)
        self.pinch_active = False
        self.current_gesture = "NONE" # NONE, FIST, PALM, PEACE, THUMBS_UP, ROCK_ON
        self.raw_frame = None        # Raw frame with landmarks drawn
        self.frame_dims = (640, 480)
        self.mirror = True
        self.show_skeleton = True
        self.fps = 0
        
        # Calibration thresholds
        self.pinch_threshold = 40  # Distance in pixels to trigger pinch
        
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def _classify_gesture(self, landmarks):
        """Classifies static hand postures based on finger extension joint geometry."""
        lm = landmarks.landmark
        
        # Determine if index, middle, ring, pinky are extended (tip higher than PIP joint)
        index_open = lm[8].y < lm[6].y
        middle_open = lm[12].y < lm[10].y
        ring_open = lm[16].y < lm[14].y
        pinky_open = lm[20].y < lm[18].y
        
        # Determine if thumb is extended (tip is far from index MCP base joint)
        # Using Euclidean distance comparison to make it orientation robust
        d_tip = math.sqrt((lm[4].x - lm[5].x)**2 + (lm[4].y - lm[5].y)**2)
        d_joint = math.sqrt((lm[3].x - lm[5].x)**2 + (lm[3].y - lm[5].y)**2)
        thumb_open = d_tip > d_joint * 1.15
        
        fingers = [index_open, middle_open, ring_open, pinky_open]
        
        # Classification Matrix
        if fingers == [0, 0, 0, 0]:
            # All 4 fingers folded
            if thumb_open and lm[4].y < lm[2].y:
                return "THUMBS_UP"
            else:
                return "FIST"
        elif fingers == [1, 1, 1, 1]:
            return "PALM"
        elif fingers == [1, 1, 0, 0]:
            return "PEACE"
        elif fingers == [1, 0, 0, 1]:
            return "ROCK_ON"
            
        return "NONE"
        
    def _run(self):
        # Initialize media pipe hands in the thread
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if cv2.os.name == 'nt' else cv2.CAP_ANY)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        prev_time = time.time()
        
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)
                self.cap = cv2.VideoCapture(self.camera_index)
                continue
                
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                
            if self.mirror:
                frame = cv2.flip(frame, 1)
                
            h, w, _ = frame.shape
            self.frame_dims = (w, h)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            index_pos = None
            thumb_pos = None
            pinch = False
            gesture = "NONE"
            
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                
                # Extract landmarks for Index Tip (8) and Thumb Tip (4)
                idx_lm = hand_landmarks.landmark[8]
                thumb_lm = hand_landmarks.landmark[4]
                
                # Convert coordinates to pixels
                idx_x, idx_y = int(idx_lm.x * w), int(idx_lm.y * h)
                thumb_x, thumb_y = int(thumb_lm.x * w), int(thumb_lm.y * h)
                
                index_pos = (idx_x, idx_y)
                thumb_pos = (thumb_x, thumb_y)
                
                # Pinch check
                dist = math.sqrt((idx_x - thumb_x)**2 + (idx_y - thumb_y)**2)
                if dist < self.pinch_threshold:
                    pinch = True
                    
                # Classify static gesture
                gesture = self._classify_gesture(hand_landmarks)
                
                # Draw skeleton and labels
                if self.show_skeleton:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    color = (0, 255, 0) if pinch else (0, 0, 255)
                    cv2.line(frame, (idx_x, idx_y), (thumb_x, thumb_y), color, 2)
                    cv2.circle(frame, (idx_x, idx_y), 6, (255, 0, 255), -1)
                    cv2.circle(frame, (thumb_x, thumb_y), 6, (255, 0, 255), -1)
                    
                    # Draw gesture text overlay in webcam view
                    cv2.putText(frame, f"Gesture: {gesture}", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # FPS Calculation
            curr_time = time.time()
            self.fps = int(1.0 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time
            
            # Thread-safe write
            with self.lock:
                self.index_coords = index_pos
                self.thumb_coords = thumb_pos
                self.pinch_active = pinch
                self.current_gesture = gesture
                self.raw_frame = frame
                
            time.sleep(0.001)  # Yield CPU slice
            
        # Cleanup
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.hands:
            self.hands.close()
            
    def get_data(self):
        with self.lock:
            return {
                "index": self.index_coords,
                "thumb": self.thumb_coords,
                "pinch": self.pinch_active,
                "gesture": self.current_gesture,
                "dims": self.frame_dims,
                "fps": self.fps
            }
            
    def get_frame(self):
        with self.lock:
            if self.raw_frame is not None:
                return self.raw_frame.copy()
            return None
            
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
