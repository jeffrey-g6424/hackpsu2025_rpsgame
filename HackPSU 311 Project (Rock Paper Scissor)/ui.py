import ctypes
import os
import tkinter as tk

# Absolute path to the compiled dynamic library.
# Assuming ui.py is in the same folder as librps.dylib.
LIB_PATH = os.path.join(os.path.dirname(__file__), "librps.dylib")

# Load the shared library that we built from rps.c
rps_lib = ctypes.CDLL(LIB_PATH)

# Mirror the C struct rps_round_t in Python so ctypes can understand it.
class RpsRound(ctypes.Structure):
    _fields_ = [
        ("player_move", ctypes.c_int),  # matches rps_round_t.player_move in C
        ("cpu_move", ctypes.c_int),     # matches rps_round_t.cpu_move in C
        ("result", ctypes.c_int),       # matches rps_round_t.result in C
    ]

# Tell ctypes about the C function signatures, so Python knows how to call them.
rps_lib.rps_seed.argtypes = []
rps_lib.rps_seed.restype = None

rps_lib.rps_play_round.argtypes = [ctypes.c_int, ctypes.POINTER(RpsRound)]
rps_lib.rps_play_round.restype = None

# We call rps_seed() once so the RNG inside C is randomized for this run.
rps_lib.rps_seed()

# Helper maps so we can turn numeric codes from C into readable text.
MOVE_NAMES = {
    0: "ROCK",
    1: "PAPER",
    2: "SCISSORS"
}

RESULT_NAMES = {
    0: "It's a TIE.",
    1: "You WIN!",
    2: "Computer WINS!"
}

# --------------------
# Tkinter UI setup
# --------------------

root = tk.Tk()
root.title("Rock Paper Scissors (C-powered)")
root.geometry("420x360")  # Just a comfortable window size

title_label = tk.Label(
    root,
    text="Rock Paper Scissors",
    font=("Helvetica", 18, "bold")
)
title_label.pack(pady=10)

status_label = tk.Label(
    root,
    text="Click a move to play.",
    font=("Helvetica", 12)
)
status_label.pack(pady=5)

player_label = tk.Label(root, text="You chose: -", font=("Helvetica", 12))
cpu_label = tk.Label(root, text="Computer chose: -", font=("Helvetica", 12))
result_label = tk.Label(root, text="Result: -", font=("Helvetica", 14, "bold"))

player_label.pack(pady=4)
cpu_label.pack(pady=4)
result_label.pack(pady=10)

# Frame to hold the move buttons (ROCK / PAPER / SCISSORS)
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

def play(move_int):
    """
    play(move_int) runs ONE ROUND of RPS by calling the C backend.

    move_int:
        0 for ROCK,
        1 for PAPER,
        2 for SCISSORS.
    """
    round_out = RpsRound()  # Create an empty struct for C to fill.

    # Call into the compiled C function:
    # rps_play_round(int32_t player_move, rps_round_t *out_round)
    rps_lib.rps_play_round(move_int, ctypes.byref(round_out))

    # Extract values that C wrote into round_out.
    p = round_out.player_move
    c = round_out.cpu_move
    r = round_out.result

    # Update labels in the GUI to reflect that round.
    player_label.config(text=f"You chose: {MOVE_NAMES.get(p, '?')}")
    cpu_label.config(text=f"Computer chose: {MOVE_NAMES.get(c, '?')}")
    result_label.config(text=f"Result: {RESULT_NAMES.get(r, '?')}")

    # Let the user know they can either hit Play Again or pick another move.
    status_label.config(text="Round complete. Play again?")

def reset_round():
    """
    reset_round() "clears the board" for the next round.
    This gives the vibe of starting fresh.
    """
    player_label.config(text="You chose: -")
    cpu_label.config(text="Computer chose: -")
    result_label.config(text="Result: -")
    status_label.config(text="Click a move to play.")

# Main three move buttons:
rock_btn = tk.Button(
    button_frame,
    text="ROCK",
    width=10,
    height=2,
    command=lambda: play(0)
)
paper_btn = tk.Button(
    button_frame,
    text="PAPER",
    width=10,
    height=2,
    command=lambda: play(1)
)
scissors_btn = tk.Button(
    button_frame,
    text="SCISSORS",
    width=10,
    height=2,
    command=lambda: play(2)
)

rock_btn.grid(row=0, column=0, padx=10, pady=5)
paper_btn.grid(row=0, column=1, padx=10, pady=5)
scissors_btn.grid(row=0, column=2, padx=10, pady=5)

# --- NEW: "Play Again" button ---
# This button doesn't talk to C. It just resets the UI so it looks like a new round.
again_frame = tk.Frame(root)
again_frame.pack(pady=20)

again_btn = tk.Button(
    again_frame,
    text="Play Again",
    width=12,
    height=2,
    command=reset_round
)
again_btn.pack()

# Start the Tk event loop to keep the window open and responsive.
root.mainloop()
