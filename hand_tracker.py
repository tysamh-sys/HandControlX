import cv2
import mediapipe as mp
import threading
import math
import time

class HandTracker:
    """
    A class that runs MediaPipe hand tracking in a background daemon thread
    to capture, process, and classify gestures in real time without blocking
    the main application rendering loop.
    """
    def __init__(self, camera_index=0, detection_confidence=0.7, tracking_confidence=0.7):
        self.camera_index = camera_index
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        self.mp_hands = mp.solutions.hands
        self.hands = None
        
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Thread-safe outputs
        self.current_gesture = "NONE"  # UP, DOWN, LEFT, RIGHT, NONE
        self.annotated_frame = None    # Webcam frame with custom HUD overlays
        self.frame_dims = (640, 480)
        self.fps = 0
        
    def start(self):
        """Starts the background tracking thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def _classify_gesture(self, landmarks):
        """
        Classifies gestures based on scale-invariant and orientation-invariant
        finger extension ratios (straight vs folded).
        """
        lm = landmarks.landmark
        w, h = self.frame_dims
        
        # Convert landmarks to pixel positions
        points = []
        for i in range(21):
            pt_x = int(lm[i].x * w)
            pt_y = int(lm[i].y * h)
            points.append((pt_x, pt_y))
            
        def dist(p1, p2):
            return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            
        # Helper to calculate finger extension ratio (MCP -> TIP straight line / total segment length)
        def get_extension_ratio(mcp, pip, dip, tip):
            d1 = dist(points[mcp], points[pip])
            d2 = dist(points[pip], points[dip])
            d3 = dist(points[dip], points[tip])
            s = dist(points[mcp], points[tip])
            total_len = d1 + d2 + d3
            if total_len == 0:
                return 0.0
            return s / total_len

        # Get ratios for 4 main fingers
        index_ratio = get_extension_ratio(5, 6, 7, 8)
        middle_ratio = get_extension_ratio(9, 10, 11, 12)
        ring_ratio = get_extension_ratio(13, 14, 15, 16)
        pinky_ratio = get_extension_ratio(17, 18, 19, 20)
        
        # Binary state thresholds
        index_ext = index_ratio > 0.78
        middle_ext = middle_ratio > 0.78
        ring_ext = ring_ratio > 0.78
        pinky_ext = pinky_ratio > 0.78
        
        index_fold = index_ratio < 0.55
        middle_fold = middle_ratio < 0.55
        ring_fold = ring_ratio < 0.55
        pinky_fold = pinky_ratio < 0.55
        
        # 1. Closed Fist -> DOWN (Move Down)
        if index_fold and middle_fold and ring_fold and pinky_fold:
            return "DOWN"
            
        # 2. Open Hand -> UP (Move Up)
        if index_ext and middle_ext and ring_ext and pinky_ext:
            return "UP"
            
        # 3. Pointing Left or Right (Index extended, others folded)
        if index_ext and middle_fold and ring_fold and pinky_fold:
            dx = points[8][0] - points[5][0]
            dy = points[8][1] - points[5][1]
            index_len = dist(points[5], points[6]) + dist(points[6], points[7]) + dist(points[7], points[8])
            
            # Pointing Left (mirrored coordinates)
            if dx < -0.4 * index_len and abs(dx) > abs(dy):
                return "LEFT"
            # Pointing Right (mirrored coordinates)
            if dx > 0.4 * index_len and abs(dx) > abs(dy):
                return "RIGHT"
                
        return "NONE"

    def _draw_custom_hud(self, frame, hand_landmarks):
        """Draws a premium cyberpunk style skeleton and connection HUD overlay."""
        lm = hand_landmarks.landmark
        w, h = self.frame_dims
        
        # Convert landmarks to pixel positions
        points = []
        for i in range(21):
            pt_x = int(lm[i].x * w)
            pt_y = int(lm[i].y * h)
            points.append((pt_x, pt_y))
            
        # Standard MediaPipe Hand Connections
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),      # Index
            (9, 10), (10, 11), (11, 12),         # Middle
            (13, 14), (14, 15), (15, 16),        # Ring
            (0, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (5, 9), (9, 13), (13, 17)            # Palm knuckles
        ]
        
        # Draw skeleton connections (glowing neon cyan lines)
        for parent, child in connections:
            pt1 = points[parent]
            pt2 = points[child]
            # Glow effect
            cv2.line(frame, pt1, pt2, (255, 80, 0), 4, cv2.LINE_AA)       # Subdued dark blue glow
            cv2.line(frame, pt1, pt2, (255, 230, 0), 1, cv2.LINE_AA)      # Bright cyan inner line
            
        # Draw joints (magenta nodes with white core)
        for i, pt in enumerate(points):
            # Base joints vs tips
            if i in [4, 8, 12, 16, 20]:  # Tips
                cv2.circle(frame, pt, 7, (0, 0, 255), -1, cv2.LINE_AA)    # Outer red/magenta glow
                cv2.circle(frame, pt, 3, (255, 255, 255), -1, cv2.LINE_AA)# White core
            else:
                cv2.circle(frame, pt, 5, (180, 0, 255), -1, cv2.LINE_AA)  # Magenta joints
                cv2.circle(frame, pt, 2, (255, 255, 255), -1, cv2.LINE_AA)# White core
                
    def _run(self):
        # Initialize MediaPipe Hands inside background thread
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        
        # Open webcam capture
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
                
            # Mirror the frame so visual left matches physical right (and vice versa)
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            self.frame_dims = (w, h)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            gesture = "NONE"
            
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                gesture = self._classify_gesture(hand_landmarks)
                self._draw_custom_hud(frame, hand_landmarks)
                
            # Calculate FPS
            curr_time = time.time()
            self.fps = int(1.0 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time
            
            # Thread-safe write to outputs
            with self.lock:
                self.current_gesture = gesture
                self.annotated_frame = frame
                self.hand_detected = (results.multi_hand_landmarks is not None)
                
            time.sleep(0.001)
            
        # Clean up
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.hands:
            self.hands.close()
            
    def get_data(self):
        """Thread-safe access to status variables."""
        with self.lock:
            return {
                "gesture": self.current_gesture,
                "fps": self.fps,
                "dims": self.frame_dims,
                "hand_detected": getattr(self, 'hand_detected', False)
            }
            
    def get_frame(self):
        """Thread-safe access to processed frame."""
        with self.lock:
            if self.annotated_frame is not None:
                return self.annotated_frame.copy()
            return None
            
    def stop(self):
        """Stops the tracking loop and joins the thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
