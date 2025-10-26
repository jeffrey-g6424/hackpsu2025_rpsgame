import os
import ctypes
import tkinter as tk
from tkinter import ttk
import cv2
import mediapipe as mp
from PIL import Image, ImageTk
from collections import deque


# ========== 1. Load C backend ==========

LIB_PATH = os.path.join(os.path.dirname(__file__), "librps.dylib")
rps_lib = ctypes.CDLL(LIB_PATH)

class RpsRound(ctypes.Structure):
    _fields_ = [
        ("player_move", ctypes.c_int),
        ("cpu_move", ctypes.c_int),
        ("result", ctypes.c_int),
    ]

rps_lib.rps_seed.argtypes = []
rps_lib.rps_seed.restype = None

rps_lib.rps_play_round.argtypes = [ctypes.c_int, ctypes.POINTER(RpsRound)]
rps_lib.rps_play_round.restype = None

rps_lib.rps_move_to_string.argtypes = [ctypes.c_int]
rps_lib.rps_move_to_string.restype = ctypes.c_char_p

rps_lib.rps_result_to_string.argtypes = [ctypes.c_int]
rps_lib.rps_result_to_string.restype = ctypes.c_char_p

rps_lib.rps_seed()

RPS_ROCK = 0
RPS_PAPER = 1
RPS_SCISSORS = 2


# ========== 2. Hand / gesture detection ==========

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

def classify_gesture_from_landmarks(hand_landmarks, frame_width, frame_height):
    lm = []
    for i in range(21):
        x = int(hand_landmarks.landmark[i].x * frame_width)
        y = int(hand_landmarks.landmark[i].y * frame_height)
        lm.append((x, y))

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    fingers_extended = 0
    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        tip_y = lm[tip_idx][1]
        pip_y = lm[pip_idx][1]
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
    if move_int is None:
        return "-"
    return rps_lib.rps_move_to_string(move_int).decode("utf-8")

def result_to_string(result_int):
    return rps_lib.rps_result_to_string(result_int).decode("utf-8")



# ========== 3. Styled App Class ==========

class RPSCameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Rock Paper Scissors - Camera Edition")

        # --- DARK MODE THEME SETUP ---
        bg_main     = "#1e1e1e"  # window background
        bg_panel    = "#2a2a2a"  # card panels
        fg_text     = "#ffffff"  # normal text
        fg_dim      = "#9ca3af"  # subtle text (gray-400 ish)
        accent_bg   = "#3b82f6"  # start button blue
        accent_bg_h = "#2563eb"  # hover blue
        danger_bg   = "#ef4444"  # quit red
        danger_bg_h = "#dc2626"
        border_col  = "#3f3f46"  # subtle border gray

        self.colors = {
            "bg_main": bg_main,
            "bg_panel": bg_panel,
            "fg_text": fg_text,
            "fg_dim": fg_dim,
            "accent_bg": accent_bg,
            "accent_bg_h": accent_bg_h,
            "danger_bg": danger_bg,
            "danger_bg_h": danger_bg_h,
            "border_col": border_col
        }
        self.master.configure(bg=bg_main)

        # ttk style overrides
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "Main.TFrame",
            background=bg_main,
        )
        style.configure(
            "Panel.TFrame",
            background=bg_panel,
            borderwidth=1,
            relief="solid"
        )
        style.map(
            "Panel.TFrame",
            background=[("active", bg_panel)]
        )

        style.configure(
            "TLabel",
            background=bg_panel,
            foreground=fg_text,
            font=("Helvetica", 11)
        )
        style.configure(
            "Dim.TLabel",
            background=bg_panel,
            foreground=fg_dim,
            font=("Helvetica", 10)
        )
        style.configure(
            "Title.TLabel",
            background=bg_main,
            foreground=fg_text,
            font=("Helvetica", 18, "bold")
        )
        style.configure(
            "Countdown.TLabel",
            background=bg_panel,
            foreground="#ef4444",  # red
            font=("Helvetica", 26, "bold")
        )
        style.configure(
            "Outcome.TLabel",
            background=bg_panel,
            foreground="#ffffff",
            font=("Helvetica", 16, "bold")
        )
        style.configure(
            "Live.TLabel",
            background=bg_panel,
            foreground="#a5b4fc",
            font=("Helvetica", 12, "bold")
        )


        # --- GAME STATE ---
        self.ROUND_COUNTDOWN = 3
        self.in_round = False
        self.countdown_remaining = 0
        self.countdown_job = None

        self.round_predictions = deque(maxlen=60)

        self.last_player_move = None
        self.last_cpu_move = None
        self.last_result = None

        # camera
        self.cap = cv2.VideoCapture(0)
        self.current_frame_image = None
        self.current_live_gesture = None

        # --- LAYOUT ---
        #Main wrapper frame just to control padding
        self.outer = ttk.Frame(self.master, style="Main.TFrame", padding=20)
        self.outer.pack(fill="both", expand=True)

        #Title row
        self.title_label = ttk.Label(
            self.outer,
            text="Rock Paper Scissors Game with Camera Input",
            style="Title.TLabel"
        )
        self.title_label.pack(anchor="w", pady=(0, 15))

        #Layout:
        #Left column: camera panel + live status panel
        #Right column: results panel + controls
        self.columns = ttk.Frame(self.outer, style="Main.TFrame")
        self.columns.pack(fill="both", expand=True)

        #LEFT SIDE
        self.left_col = ttk.Frame(self.columns, style="Main.TFrame")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        #RIGHT SIDE
        self.right_col = ttk.Frame(self.columns, style="Main.TFrame")
        self.right_col.grid(row=0, column=1, sticky="nsew")

        #Make columns expand
        self.columns.columnconfigure(0, weight=1)
        self.columns.columnconfigure(1, weight=0)
        self.columns.rowconfigure(0, weight=1)

        # ---- Camera Panel ----
        self.camera_panel = ttk.Frame(
            self.left_col,
            style="Panel.TFrame",
            padding=12
        )
        self.camera_panel.pack(fill="both", expand=True)

        self.video_label = ttk.Label(
            self.camera_panel,
            style="TLabel",
            text="(camera initializing...)"
        )
        self.video_label.pack()

        # ---- Round Status Panel ----
        self.status_panel = ttk.Frame(
            self.left_col,
            style="Panel.TFrame",
            padding=12
        )
        self.status_panel.pack(fill="x", expand=False, pady=(15, 0))

        self.status_label = ttk.Label(
            self.status_panel,
            text="Press 'Start Round' and show ✊ ROCK / ✋ PAPER / ✌️ SCISSORS",
            style="TLabel",
            wraplength=500,
            justify="left"
        )
        self.status_label.pack(anchor="w")

        #countdown row
        self.countdown_label = ttk.Label(
            self.status_panel,
            text="",
            style="Countdown.TLabel"
        )
        self.countdown_label.pack(anchor="center", pady=(8, 4))

        #live gesture label
        self.live_gesture_label = ttk.Label(
            self.status_panel,
            text="Live gesture: -",
            style="Live.TLabel"
        )
        self.live_gesture_label.pack(anchor="center")

        self.hint_label = ttk.Label(
            self.status_panel,
            text="(Hold a clear pose while timer runs)",
            style="Dim.TLabel"
        )
        self.hint_label.pack(anchor="center", pady=(4, 0))

        # ---- Results Panel ----
        self.results_panel = ttk.Frame(
            self.right_col,
            style="Panel.TFrame",
            padding=12
        )
        self.results_panel.pack(fill="x", expand=False)

        self.results_title = ttk.Label(
            self.results_panel,
            text="Last Round",
            style="TLabel",
            font=("Helvetica", 14, "bold")
        )
        self.results_title.pack(anchor="w", pady=(0, 8))

        self.player_choice_label = ttk.Label(
            self.results_panel,
            text="Your move: -",
            style="TLabel"
        )
        self.player_choice_label.pack(anchor="w", pady=2)

        self.cpu_choice_label = ttk.Label(
            self.results_panel,
            text="Computer move: -",
            style="TLabel"
        )
        self.cpu_choice_label.pack(anchor="w", pady=2)

        self.outcome_label = ttk.Label(
            self.results_panel,
            text="Result: -",
            style="Outcome.TLabel"
        )
        self.outcome_label.pack(anchor="w", pady=(8, 4))

        # ---- Controls Panel ----
        self.controls_panel = ttk.Frame(
            self.right_col,
            style="Panel.TFrame",
            padding=12
        )
        self.controls_panel.pack(fill="x", expand=False, pady=(15, 0))

        #Custom buttons (using tk.Button so the colors can be changed)
        self.start_button = tk.Button(
            self.controls_panel,
            text="Play Again / Start Round",
            font=("Helvetica", 12, "bold"),
            fg="#000000",
            bg=accent_bg,
            activeforeground="#ffffff",
            activebackground=accent_bg_h,
            bd=0,
            padx=16,
            pady=10,
            relief="flat",
            highlightthickness=0,
            command=self.start_round
        )
        self.start_button.pack(fill="x", pady=(0, 10))

        self.quit_button = tk.Button(
            self.controls_panel,
            text="Quit",
            font=("Helvetica", 12, "bold"),
            fg="#000000",
            bg=danger_bg,
            activeforeground="#ffffff",
            activebackground=danger_bg_h,
            bd=0,
            padx=16,
            pady=10,
            relief="flat",
            highlightthickness=0,
            command=self.on_close
        )
        self.quit_button.pack(fill="x")

        #Hover effects for buttons
        def hover_on_start(e):
            self.start_button.config(bg=accent_bg_h)
        def hover_off_start(e):
            self.start_button.config(bg=accent_bg)
        self.start_button.bind("<Enter>", hover_on_start)
        self.start_button.bind("<Leave>", hover_off_start)

        def hover_on_quit(e):
            self.quit_button.config(bg=danger_bg_h)
        def hover_off_quit(e):
            self.quit_button.config(bg=danger_bg)
        self.quit_button.bind("<Enter>", hover_on_quit)
        self.quit_button.bind("<Leave>", hover_off_quit)

        #subtle borders for panels to make them feel like "cards"
        for panel in [self.camera_panel, self.status_panel, self.results_panel, self.controls_panel]:
            panel.configure(style="Panel.TFrame")
            panel.configure(borderwidth=1)
            panel.configure(relief="solid")
        style.configure("Panel.TFrame", background=bg_panel, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col)

        #Make sure background of parent frames matches theme
        self.left_col.configure(style="Main.TFrame")
        self.right_col.configure(style="Main.TFrame")

        #start pulling frames from camera
        self.master.after(30, self.update_camera_frame)

        #clean shutdown hook
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    #
    # ========== Round flow ==========
    #

    def start_round(self):
        if self.in_round:
            return

        self.in_round = True
        self.countdown_remaining = self.ROUND_COUNTDOWN
        self.round_predictions.clear()

        self.last_player_move = None
        self.last_cpu_move = None
        self.last_result = None

        self.player_choice_label.config(text="Your move: -")
        self.cpu_choice_label.config(text="Computer move: -")
        self.outcome_label.config(text="Result: -")

        self.status_label.config(
            text="Show ✊ ROCK / ✋ PAPER / ✌️ SCISSORS clearly to the camera!"
        )
        self.countdown_label.config(text=str(self.countdown_remaining))

        #Disable start button during round
        self.start_button.config(state="disabled")

        self.schedule_next_countdown_tick()

    def schedule_next_countdown_tick(self):
        self.countdown_job = self.master.after(1000, self.countdown_tick)

    def countdown_tick(self):
        if not self.in_round:
            return

        self.countdown_remaining -= 1

        if self.countdown_remaining > 0:
            self.countdown_label.config(text=str(self.countdown_remaining))
            self.schedule_next_countdown_tick()
        else:
            self.countdown_label.config(text="Shoot!")
            self.countdown_job = self.master.after(500, self.finish_round)

    def finish_round(self):
        if not self.in_round:
            return

        self.in_round = False
        self.start_button.config(state="normal")

        #Pick gesture that appeared most often
        player_move = self.choose_player_move_from_buffer()

        if player_move is None:
            self.status_label.config(
                text="No clear gesture detected 😔 Try again."
            )
            self.countdown_label.config(text="")
            return

        rnd = RpsRound()
        rps_lib.rps_play_round(player_move, ctypes.byref(rnd))

        self.last_player_move = rnd.player_move
        self.last_cpu_move = rnd.cpu_move
        self.last_result = rnd.result

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
        if len(self.round_predictions) == 0:
            return None

        counts = {}
        for g in self.round_predictions:
            if g is None:
                continue
            counts[g] = counts.get(g, 0) + 1

        if not counts:
            return None

        best_move = max(counts, key=counts.get)
        if counts[best_move] < 5:
            return None

        return best_move

    #
    # ========== Camera loop ==========
    #

    def update_camera_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            #Camera not available
            self.video_label.config(text="(No camera frame)")
            self.master.after(30, self.update_camera_frame)
            return

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_detector.process(rgb)

        predicted_move = None

        if results.multi_hand_landmarks:
            handLms = results.multi_hand_landmarks[0]
            predicted_move = classify_gesture_from_landmarks(handLms, w, h)
            mp_drawing.draw_landmarks(
                frame,
                handLms,
                mp_hands.HAND_CONNECTIONS
            )

        self.current_live_gesture = predicted_move

        if self.in_round:
            self.round_predictions.append(predicted_move)

        #Overlay text feedback directly onto frame
        overlay_lines = []
        if self.in_round:
            overlay_lines.append("ROUND ACTIVE: Show your move!")
        else:
            overlay_lines.append("Idle. Press Start Round.")
        overlay_lines.append(f"Live: {move_to_string(self.current_live_gesture)}")

        y0 = 30
        for i, line in enumerate(overlay_lines):
            cv2.putText(
                frame,
                line,
                (10, y0 + i * 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        #Update "live gesture" label in the side panel
        self.live_gesture_label.config(
            text=f"Live gesture: {move_to_string(self.current_live_gesture)}"
        )

        #Convert frame for Tk
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        #Scale preview to a max width (nice fit in panel)
        display_w = 480
        scale = display_w / pil_img.width
        display_h = int(pil_img.height * scale)
        pil_img = pil_img.resize((display_w, display_h))

        tk_img = ImageTk.PhotoImage(image=pil_img)
        self.current_frame_image = tk_img
        self.video_label.config(image=tk_img)
        self.video_label.image = tk_img

        self.master.after(30, self.update_camera_frame)

    #
    # ========== Cleanup ==========
    #

    def on_close(self):
        if self.countdown_job is not None:
            try:
                self.master.after_cancel(self.countdown_job)
            except Exception:
                pass

        if self.cap.isOpened():
            self.cap.release()

        self.master.destroy()


#
# ========== 4. Run app ==========
#

if __name__ == "__main__":
    root = tk.Tk()
    app = RPSCameraApp(root)
    root.mainloop()
