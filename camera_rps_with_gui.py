import os
import ctypes
import tkinter as tk
from tkinter import ttk
import cv2
import mediapipe as mp
from PIL import Image, ImageTk
from collections import deque

#
# =========================
# 1. Load the C backend (librps.dylib)
# =========================
#
# Assume librps.dylib is in the same folder. My C library has:
#   rps_seed()
#   rps_play_round(int player_move, rps_round_t* out_round)
#   rps_move_to_string(...)
#   rps_result_to_string(...)
# which is already written in C.
#

LIB_PATH = os.path.join(os.path.dirname(__file__), "librps.dylib")
rps_lib = ctypes.CDLL(LIB_PATH)

class RpsRound(ctypes.Structure):
    _fields_ = [
        ("player_move", ctypes.c_int),
        ("cpu_move", ctypes.c_int),
        ("result", ctypes.c_int),
    ]

#Tell ctypes about function signatures.
rps_lib.rps_seed.argtypes = []
rps_lib.rps_seed.restype = None

rps_lib.rps_play_round.argtypes = [ctypes.c_int, ctypes.POINTER(RpsRound)]
rps_lib.rps_play_round.restype = None

rps_lib.rps_move_to_string.argtypes = [ctypes.c_int]
rps_lib.rps_move_to_string.restype = ctypes.c_char_p

rps_lib.rps_result_to_string.argtypes = [ctypes.c_int]
rps_lib.rps_result_to_string.restype = ctypes.c_char_p

#Seed RNG inside the C code so CPU move is randomized.
rps_lib.rps_seed()

#Mirror the enum meanings for readability.
RPS_ROCK = 0
RPS_PAPER = 1
RPS_SCISSORS = 2

#
# =========================
# 2. Hand / gesture classification helpers
# =========================
#

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

#Build a single-hands tracker.
hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

def classify_gesture_from_landmarks(hand_landmarks, frame_width, frame_height):
    """
    Look at finger extension to guess ROCK / PAPER / SCISSORS.
    We'll count how many non-thumb fingers are "up":
    - ROCK      -> 0 or 1 fingers extended
    - PAPER     -> 4+ fingers extended (open palm)
    - SCISSORS  -> exactly 2 fingers extended
    Otherwise   -> None (unrecognized / in-between)
    """

    #Grab all 21 normalized points and turn them into pixel coordinates.
    lm = []
    for i in range(21):
        x = int(hand_landmarks.landmark[i].x * frame_width)
        y = int(hand_landmarks.landmark[i].y * frame_height)
        lm.append((x, y))

    #Indices for fingertips/PIP for index, middle, ring, pinky:
    #   tip: 8,12,16,20
    #   pip: 6,10,14,18
    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    fingers_extended = 0
    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        tip_y = lm[tip_idx][1]
        pip_y = lm[pip_idx][1]
        #y is "down" in image, so tip_y < pip_y means finger is raised/straight
        if tip_y < pip_y:
            fingers_extended += 1

    if fingers_extended <= 1:
        return RPS_ROCK
    elif fingers_extended >= 4:
        return RPS_PAPER
    elif fingers_extended == 2:
        return RPS_SCISSORS
    else:
        return None

def move_to_string(move_int):
    """Ask C backend for the official move string."""
    if move_int is None:
        return "-"
    return rps_lib.rps_move_to_string(move_int).decode("utf-8")

def result_to_string(result_int):
    """Ask C backend for official result text ("You WIN!", etc.)."""
    return rps_lib.rps_result_to_string(result_int).decode("utf-8")

#
# =========================
# 3. GUI App class
# =========================
#

class RPSCameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Rock Paper Scissors - Camera Edition")
        self.master.geometry("800x600")

        # --- Game state ---
        self.ROUND_COUNTDOWN = 3    #How much time for the player to decide
        self.in_round = False       #True while countdown is active
        self.countdown_remaining = 0
        self.countdown_job = None   #after() id so cancel if needed

        #Store recent gesture predictions from camera for stability.
        #During the countdown, record them and choose the dominant one at the end.
        self.round_predictions = deque(maxlen=60)  # ~2 seconds at 30fps

        #Last locked round info to display after countdown ends
        self.last_player_move = None
        self.last_cpu_move = None
        self.last_result = None

        # --- Camera / CV setup ---
        self.cap = cv2.VideoCapture(0)  #open default webcam
        self.current_frame_image = None  #keep a reference so Tk doesn't GC it

        #Keep a "live guess" of what gesture the camera currently sees
        self.current_live_gesture = None

        # --- Layout / Widgets ---
        self.build_widgets()

        #Start the continuous video refresh loop
        self.update_camera_frame()

        #Handle window close cleanly
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_widgets(self):
        #Top title
        self.title_label = ttk.Label(
            self.master,
            text="Rock Paper Scissors (C-powered, Camera Input)",
            font=("Helvetica", 16, "bold")
        )
        self.title_label.pack(pady=10)

        #Frame where camera preview will live
        self.video_frame = ttk.Frame(self.master)
        self.video_frame.pack()

        #Label that will display the live camera image
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack()

        #Countdown / status row
        self.status_frame = ttk.Frame(self.master)
        self.status_frame.pack(pady=10)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Press 'Start Round' and show ROCK ✊ / PAPER ✋ / SCISSORS ✌️",
            font=("Helvetica", 11)
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.countdown_label = ttk.Label(
            self.status_frame,
            text="",
            font=("Helvetica", 20, "bold"),
            foreground="red"
        )
        self.countdown_label.grid(row=0, column=1, padx=20, pady=5)

        #Live gesture reading label
        self.live_gesture_label = ttk.Label(
            self.master,
            text="Live gesture: -",
            font=("Helvetica", 12)
        )
        self.live_gesture_label.pack(pady=5)

        #Results from the 'last' finished round
        self.results_frame = ttk.Frame(self.master)
        self.results_frame.pack(pady=10)

        self.player_choice_label = ttk.Label(
            self.results_frame,
            text="Your move: -",
            font=("Helvetica", 12)
        )
        self.player_choice_label.grid(row=0, column=0, padx=10, pady=4, sticky="w")

        self.cpu_choice_label = ttk.Label(
            self.results_frame,
            text="Computer move: -",
            font=("Helvetica", 12)
        )
        self.cpu_choice_label.grid(row=1, column=0, padx=10, pady=4, sticky="w")

        self.outcome_label = ttk.Label(
            self.results_frame,
            text="Result: -",
            font=("Helvetica", 14, "bold")
        )
        self.outcome_label.grid(row=2, column=0, padx=10, pady=8, sticky="w")

        #Control buttons frame
        self.controls_frame = ttk.Frame(self.master)
        self.controls_frame.pack(pady=20)

        self.start_button = ttk.Button(
            self.controls_frame,
            text="Play Again / Start Round",
            command=self.start_round
        )
        self.start_button.grid(row=0, column=0, padx=10)

        self.quit_button = ttk.Button(
            self.controls_frame,
            text="Quit",
            command=self.on_close
        )
        self.quit_button.grid(row=0, column=1, padx=10)

    #
    # =========================
    # Round flow
    # =========================
    #

    def start_round(self):
        """Begin a new timed round with a countdown."""
        if self.in_round:
            #Already running a round; ignore double-clicks.
            return

        #Reset round state
        self.in_round = True
        self.countdown_remaining = self.ROUND_COUNTDOWN
        self.round_predictions.clear()

        #Clear previous result display
        self.last_player_move = None
        self.last_cpu_move = None
        self.last_result = None
        self.player_choice_label.config(text="Your move: -")
        self.cpu_choice_label.config(text="Computer move: -")
        self.outcome_label.config(text="Result: -")

        self.status_label.config(
            text="Show ROCK ✊ / PAPER ✋ / SCISSORS ✌️ to the camera!"
        )
        self.countdown_label.config(text=str(self.countdown_remaining))

        #Disable start during the countdown so you can't spam it
        self.start_button.state(["disabled"])

        #Kick off countdown ticks
        self.schedule_next_countdown_tick()

    def schedule_next_countdown_tick(self):
        """Schedule the next 1-second countdown tick."""
        #Use after() so Tkinter stays responsive.
        self.countdown_job = self.master.after(1000, self.countdown_tick)

    def countdown_tick(self):
        """Called every second while the round is active."""
        if not self.in_round:
            return  #Safety: if round got canceled somehow.

        self.countdown_remaining -= 1

        if self.countdown_remaining > 0:
            #Update number and keep going
            self.countdown_label.config(text=str(self.countdown_remaining))
            self.schedule_next_countdown_tick()
        else:
            #Countdown hit 0: lock in choice and judge the round
            self.countdown_label.config(text="Shoot!")
            #Give a short dramatic pause (0.5s) before locking
            self.countdown_job = self.master.after(500, self.finish_round)

    def finish_round(self):
        """End the round, pick the player's final gesture, ask C to judge."""
        if not self.in_round:
            return

        self.in_round = False

        #Re-enable Start button so the user can play again.
        self.start_button.state(["!disabled"])

        #Figure out which gesture was most common during the countdown.
        player_move = self.choose_player_move_from_buffer()

        if player_move is None:
            #Could not read a stable gesture
            self.status_label.config(
                text="No clear gesture detected. Try again!"
            )
            self.countdown_label.config(text="")
            return

        #Call into the C game logic to actually play the round.
        rnd = RpsRound()
        rps_lib.rps_play_round(player_move, ctypes.byref(rnd))

        self.last_player_move = rnd.player_move
        self.last_cpu_move = rnd.cpu_move
        self.last_result = rnd.result

        #Update UI
        self.player_choice_label.config(
            text=f"Your move: {move_to_string(self.last_player_move)}"
        )
        self.cpu_choice_label.config(
            text=f"Computer move: {move_to_string(self.last_cpu_move)}"
        )
        self.outcome_label.config(
            text=f"Result: {result_to_string(self.last_result)}"
        )

        self.status_label.config(
            text="Round complete. Press 'Play Again / Start Round' for another round."
        )
        self.countdown_label.config(text="")

    def choose_player_move_from_buffer(self):
        """
        Look at the round_predictions deque (gestures recorded while timer ran).
        We'll pick the gesture that appears most often, if it appears enough times.
        """
        if len(self.round_predictions) == 0:
            return None

        counts = {}
        for g in self.round_predictions:
            if g is None:
                continue
            counts[g] = counts.get(g, 0) + 1

        if not counts:
            return None

        #Most common gesture
        best_move = max(counts, key=counts.get)
        #Basic confidence threshold: must appear at least 5 times
        if counts[best_move] < 5:
            return None

        return best_move

    #
    # =========================
    # Camera capture / updating the preview
    # =========================
    #

    def update_camera_frame(self):
        """
        Grabs a frame from the webcam, runs MediaPipe hands to guess gesture,
        overlays helper text, and pushes the frame into the Tkinter Image label.
        This function reschedules itself ~30fps using after().
        """
        ok, frame = self.cap.read()
        if not ok:
            #Camera couldn't read; show a blank frame message.
            self.video_label.config(text="(No camera frame)")
            self.master.after(30, self.update_camera_frame)
            return

        #Mirror for a more natural "selfie" view.
        frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        #Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_detector.process(rgb)

        predicted_move = None

        if results.multi_hand_landmarks:
            #Only look at the first detected hand
            handLms = results.multi_hand_landmarks[0]

            #Classify current gesture
            predicted_move = classify_gesture_from_landmarks(handLms, w, h)

            #Draw landmarks so player can see tracking
            mp_drawing.draw_landmarks(
                frame,
                results.multi_hand_landmarks[0],
                mp_hands.HAND_CONNECTIONS
            )

        #Save this live guess to display it in the UI
        self.current_live_gesture = predicted_move

        #If in the middle of a round/countdown,
        #collect predictions for final decision later.
        if self.in_round:
            self.round_predictions.append(predicted_move)

        #Overlay text onto the camera frame for player feedback.
        #Show:
        # - instruction or status
        # - what gesture we currently think we're seeing
        overlay_lines = []
        if self.in_round:
            overlay_lines.append("ROUND ACTIVE: Show your move!")
        else:
            overlay_lines.append("Idle. Press 'Start Round'.")
        overlay_lines.append(
            f"Live: {move_to_string(self.current_live_gesture)}"
        )

        y0 = 25
        for i, line in enumerate(overlay_lines):
            cv2.putText(
                frame,
                line,
                (10, y0 + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        #Also update text widget under the video
        self.live_gesture_label.config(
            text=f"Live gesture: {move_to_string(self.current_live_gesture)}"
        )

        #Convert BGR -> RGB -> PIL Image -> ImageTk PhotoImage
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        #Optionally resize preview to fit the window nicer.
        #Cap the width to ~640 for display.
        display_w = 640
        scale = display_w / pil_img.width
        display_h = int(pil_img.height * scale)
        pil_img = pil_img.resize((display_w, display_h))

        tk_img = ImageTk.PhotoImage(image=pil_img)
        self.current_frame_image = tk_img  # prevent GC
        self.video_label.config(image=tk_img)

        #Schedule next frame grab
        self.master.after(30, self.update_camera_frame)

    #
    # =========================
    # Cleanup
    # =========================
    #

    def on_close(self):
        """Release camera and close the window cleanly."""
        if self.countdown_job is not None:
            try:
                self.master.after_cancel(self.countdown_job)
            except Exception:
                pass

        if self.cap.isOpened():
            self.cap.release()

        self.master.destroy()


#
# =========================
# 4. Main entry point
# =========================
#

if __name__ == "__main__":
    root = tk.Tk()
    app = RPSCameraApp(root)
    root.mainloop()
