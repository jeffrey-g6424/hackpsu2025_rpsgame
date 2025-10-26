import cv2                 # OpenCV for camera
import mediapipe as mp     # MediaPipe Hands
import ctypes              # To call into your C .dylib
import time
from collections import deque

#
# === 1. Load the C library you already built ===
#

librps = ctypes.CDLL("./librps.dylib")

#Mirror the C enums from rps.h so Python code can stay readable.
RPS_ROCK = 0
RPS_PAPER = 1
RPS_SCISSORS = 2

RPS_RESULT_TIE = 0
RPS_RESULT_PLAYER_WIN = 1
RPS_RESULT_CPU_WIN = 2

#Mirror the rps_round_t struct layout from rps.h exactly. :contentReference[oaicite:4]{index=4}
class RPSRound(ctypes.Structure):
    _fields_ = [
        ("player_move", ctypes.c_int),  # rps_move_t is an enum (int)
        ("cpu_move", ctypes.c_int),
        ("result", ctypes.c_int)
    ]

#Declare argument / return types for the C functions we call.
librps.rps_seed.argtypes = []
librps.rps_seed.restype = None

librps.rps_play_round.argtypes = [ctypes.c_int, ctypes.POINTER(RPSRound)]
librps.rps_play_round.restype = None

#Optional (for printing readable strings from C, if you want):
librps.rps_move_to_string.argtypes = [ctypes.c_int]
librps.rps_move_to_string.restype = ctypes.c_char_p

librps.rps_result_to_string.argtypes = [ctypes.c_int]
librps.rps_result_to_string.restype = ctypes.c_char_p

#Seed the RNG once, just like main.c does before the loop. :contentReference[oaicite:5]{index=5}
librps.rps_seed()


#
# === 2. Hand detection setup (MediaPipe Hands) ===
#
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

#Use a single-hand model (max_num_hands=1) for simplicity.
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


#
# === 3. Helper: finger state estimation ===
#
def classify_gesture_from_landmarks(hand_landmarks, frame_width, frame_height):
    """
    Given MediaPipe 21 hand landmarks, return:
        0 for ROCK, 1 for PAPER, 2 for SCISSORS, or None if unknown.
    We do this by counting "extended" fingers.
    """

    #Extract (x,y) in pixel space for convenience.
    #MediaPipe gives normalized coords [0,1], so multiply.
    lm = []
    for i in range(21):
        x = int(hand_landmarks.landmark[i].x * frame_width)
        y = int(hand_landmarks.landmark[i].y * frame_height)
        lm.append((x, y))

    #Landmark indices for fingertips and PIP joints (not including thumb for now):
    #Index finger tip = 8, PIP = 6
    #Middle finger tip = 12, PIP = 10
    #Ring finger tip = 16, PIP = 14
    #Pinky tip = 20, PIP = 18

    #Rule: a finger is "extended" if tip_y < pip_y (because y grows downward in images; smaller y = higher / straighter finger)

    fingers_extended = 0

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        tip_y = lm[tip_idx][1]
        pip_y = lm[pip_idx][1]
        if tip_y < pip_y:
            fingers_extended += 1

    #Very rough classification:
    #ROCK: about0 fingers extended
    #PAPER: 4 fingers extended (open palm). We treat that as full hand.
    #SCISSORS: about 2 fingers extended (usually index+middle). We'll accept exactly 2.

    if fingers_extended <= 1:
        return RPS_ROCK       #closed fist
    elif fingers_extended >= 4:
        return RPS_PAPER      #open hand
    elif fingers_extended == 2:
        return RPS_SCISSORS   #two-finger "V"
    else:
        return None           #not sure / in-between


#
# === 4. Pretty-print helpers for overlay text ===
#
def move_to_text(move_int):
    #Ask the C library for the official string, so UI matches CLI. :contentReference[oaicite:6]{index=6}
    return librps.rps_move_to_string(move_int).decode("utf-8")

def result_to_text(result_int):
    #Ask C for the summary line ("You WIN!", etc.). :contentReference[oaicite:7]{index=7}
    return librps.rps_result_to_string(result_int).decode("utf-8")


#
# === 5. Game loop using the webcam ===
#
cap = cv2.VideoCapture(0)  # 0 = default camera

#Store the last few gesture predictions and only "lock in"
#when they agree for several frames. This helps with jitter.
recent_gestures = deque(maxlen=10)
locked_choice = None
last_round_time = 0
round_cooldown_sec = 2.0  #wait between rounds so it doesn't spam

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read from camera.")
            break

        #Flip horizontally for mirror view (so it feels natural).
        frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        #Convert BGR -> RGB for MediaPipe processing
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        predicted_move = None

        if result.multi_hand_landmarks:
            #Use the first detected hand only.
            handLms = result.multi_hand_landmarks[0]

            #Classify gesture
            predicted_move = classify_gesture_from_landmarks(handLms, w, h)

            #Draw landmarks on the frame so you can see tracking
            mp_draw.draw_landmarks(
                frame,
                handLms,
                mp_hands.HAND_CONNECTIONS
            )

        #Add current prediction (even if None) to the buffer
        recent_gestures.append(predicted_move)

        #Decide "stable_gesture" = most common non-None in the last N frames
        stable_gesture = None
        if len(recent_gestures) == recent_gestures.maxlen:
            #Count frequencies
            counts = {}
            for g in recent_gestures:
                if g is None:
                    continue
                counts[g] = counts.get(g, 0) + 1

            #Pick the gesture that appears most often
            if counts:
                stable_gesture = max(counts, key=counts.get)
                #Require it to be pretty dominant
                if counts[stable_gesture] < 6:  # tweak threshold if it's too strict/loose
                    stable_gesture = None

        #If there is a stable gesture and cooldown passed, lock it in and play a round
        now = time.time()
        if stable_gesture is not None and (now - last_round_time) > round_cooldown_sec:
            locked_choice = stable_gesture

            #Play one round via the C library, exactly like main.c does. :contentReference[oaicite:8]{index=8}
            out_round = RPSRound()
            librps.rps_play_round(ctypes.c_int(locked_choice), ctypes.byref(out_round))

            #Print to terminal for debug if necessary
            print("You:", move_to_text(out_round.player_move))
            print("CPU:", move_to_text(out_round.cpu_move))
            print("=> ", result_to_text(out_round.result))
            print("--------------------------------")

            #And remember the time so it doesn't instantly trigger again
            last_round_time = now

        #
        # === 6. Draw UI overlay on the camera feed ===
        #
        y0 = 30
        dy = 30

        cv2.putText(frame,
                    "Rock Paper Scissors - Camera Mode",
                    (10, y0),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2)

        cv2.putText(frame,
                    "Show FIST=ROCK | OPEN PALM=PAPER | V SIGN=SCISSORS",
                    (10, y0 + dy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2)

        #Show the current stable gesture guess (not yet "played")
        guess_text = "Detecting..."
        if stable_gesture is not None:
            guess_text = "Ready: " + move_to_text(stable_gesture)
        cv2.putText(frame,
                    guess_text,
                    (10, y0 + 2*dy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2)

        #Show last locked round result
        if locked_choice is not None:
            cv2.putText(frame,
                        f"Your move: {move_to_text(locked_choice)}",
                        (10, y0 + 3*dy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2)
            cv2.putText(frame,
                        "(Hold a new sign after cooldown to play again)",
                        (10, y0 + 4*dy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1)

        cv2.putText(frame,
                    "Press q to quit",
                    (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (200, 200, 200),
                    1)

        #Show the live camera window
        cv2.imshow("RPS Camera", frame)

        #Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    hands.close()
    cv2.destroyAllWindows()
