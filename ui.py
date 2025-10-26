import ctypes
import os
import tkinter as tk

# =========================
# Load C game engine (librps.dylib)
# =========================

# Path to the compiled C library containing rps_seed, rps_play_round, etc.
LIB_PATH = os.path.join(os.path.dirname(__file__), "librps.dylib")
rps_lib = ctypes.CDLL(LIB_PATH)

# Mirror the C struct rps_round_t so ctypes can read/write it.
class RpsRound(ctypes.Structure):
    _fields_ = [
        ("player_move", ctypes.c_int),   # player's move enum from C
        ("cpu_move", ctypes.c_int),      # computer's move enum from C
        ("result", ctypes.c_int),        # outcome enum from C
    ]

# Tell ctypes what the function signatures look like.
rps_lib.rps_seed.argtypes = []
rps_lib.rps_seed.restype = None

rps_lib.rps_play_round.argtypes = [ctypes.c_int, ctypes.POINTER(RpsRound)]
rps_lib.rps_play_round.restype = None

# Seed the RNG inside the C code once so the CPU move is randomized each run.
rps_lib.rps_seed()

# Human-friendly names for moves / results, matching the ints your C code uses.
MOVE_NAMES = {
    0: "ROCK",
    1: "PAPER",
    2: "SCISSORS",
}

RESULT_NAMES = {
    0: "It's a TIE.",
    1: "You WIN!",
    2: "Computer WINS!",
}

# =========================
# Tkinter UI setup
# =========================

root = tk.Tk()
root.title("Rock Paper Scissors (C-powered)")
root.geometry("460x400")

title_label = tk.Label(
    root,
    text="Rock Paper Scissors",
    font=("Helvetica", 18, "bold")
)
title_label.pack(pady=10)

status_label = tk.Label(
    root,
    text="Press 'Start Round' to begin.",
    font=("Helvetica", 12)
)
status_label.pack(pady=5)

# Big red countdown text (“3…2…1…”)
countdown_label = tk.Label(
    root,
    text="",
    font=("Helvetica", 16, "bold"),
    fg="red"
)
countdown_label.pack(pady=5)

player_label = tk.Label(root, text="You chose: -", font=("Helvetica", 12))
cpu_label = tk.Label(root, text="Computer chose: -", font=("Helvetica", 12))
result_label = tk.Label(root, text="Result: -", font=("Helvetica", 14, "bold"))

player_label.pack(pady=4)
cpu_label.pack(pady=4)
result_label.pack(pady=10)

# Frame to hold the ROCK / PAPER / SCISSORS buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# =========================
# Game state
# =========================

ROUND_COUNTDOWN = 3  # seconds; you can change to 5 if you want more reaction time
current_choice = None         # the player's selected move (0/1/2)
in_countdown = False          # whether a round is currently active
countdown_job = None          # after() timer id so we can cancel/replace if needed

def set_choice(move_int: int):
    """
    Called when the player clicks ROCK / PAPER / SCISSORS during countdown.
    We DO NOT immediately run the round here. We just remember the choice.
    """
    global current_choice
    if in_countdown:
        current_choice = move_int
        status_label.config(
            text=f"You picked {MOVE_NAMES.get(move_int, '?')}! Waiting for countdown..."
        )
    else:
        # If they mash buttons outside an active round, just tell them to start.
        status_label.config(text="Round not active. Press 'Play Again / Start Round'.")

def finish_round():
    """
    Called when the countdown finishes.
    - Disables buttons.
    - If the player did choose something, calls the C code to judge.
    """
    global in_countdown
    in_countdown = False

    # Disable move buttons until next round.
    rock_btn.config(state=tk.DISABLED)
    paper_btn.config(state=tk.DISABLED)
    scissors_btn.config(state=tk.DISABLED)

    # Re-enable the Start/Play Again button.
    again_btn.config(state=tk.NORMAL)

    if current_choice is None:
        # Player failed to choose in time.
        status_label.config(text="Time's up! You didn't pick a move.")
        countdown_label.config(text="")
        return

    # Call into the C backend to generate computer choice + result.
    rnd = RpsRound()
    rps_lib.rps_play_round(current_choice, ctypes.byref(rnd))

    p = rnd.player_move
    c = rnd.cpu_move
    r = rnd.result

    # Update labels with the outcome.
    player_label.config(text=f"You chose: {MOVE_NAMES.get(p, '?')}")
    cpu_label.config(text=f"Computer chose: {MOVE_NAMES.get(c, '?')}")
    result_label.config(text=f"Result: {RESULT_NAMES.get(r, '?')}")

    status_label.config(text="Round complete. Press 'Play Again / Start Round' to play again.")
    countdown_label.config(text="")

def run_countdown(t_left: int):
    """
    Updates the countdown label each second.
    When it reaches 0, we wait a split second and then call finish_round.
    """
    global countdown_job
    if t_left > 0:
        countdown_label.config(text=f"{t_left}")
        countdown_job = root.after(1000, run_countdown, t_left - 1)
    else:
        countdown_label.config(text="Shoot!")
        # Give half a second of dramatic pause, then resolve.
        countdown_job = root.after(500, finish_round)

def start_round():
    """
    Triggered by the "Play Again / Start Round" button.
    Resets UI, enables move buttons, starts the countdown timer.
    """
    global current_choice, in_countdown, countdown_job

    # If there's still an old countdown hanging around, cancel it.
    if countdown_job is not None:
        try:
            root.after_cancel(countdown_job)
        except Exception:
            pass

    # Reset round state.
    current_choice = None
    in_countdown = True

    player_label.config(text="You chose: -")
    cpu_label.config(text="Computer chose: -")
    result_label.config(text="Result: -")
    status_label.config(text="Pick your move before the timer ends!")
    countdown_label.config(text=str(ROUND_COUNTDOWN))

    # Enable move buttons during the countdown.
    rock_btn.config(state=tk.NORMAL)
    paper_btn.config(state=tk.NORMAL)
    scissors_btn.config(state=tk.NORMAL)

    # Disable the start button while this round is running.
    again_btn.config(state=tk.DISABLED)

    # Kick off the countdown logic.
    run_countdown(ROUND_COUNTDOWN)

def reset_round():
    """
    Optional soft reset (this is also called once at startup).
    Puts the UI in 'idle' mode before any round has started.
    """
    global current_choice, in_countdown
    current_choice = None
    in_countdown = False

    player_label.config(text="You chose: -")
    cpu_label.config(text="Computer chose: -")
    result_label.config(text="Result: -")
    status_label.config(text="Press 'Start Round' to begin.")
    countdown_label.config(text="")

    # Disable move buttons while idle.
    rock_btn.config(state=tk.DISABLED)
    paper_btn.config(state=tk.DISABLED)
    scissors_btn.config(state=tk.DISABLED)

    # Make sure Play Again / Start Round is clickable.
    again_btn.config(state=tk.NORMAL)

# =========================
# Buttons (ROCK / PAPER / SCISSORS)
# =========================

rock_btn = tk.Button(
    button_frame,
    text="ROCK",
    width=10,
    height=2,
    state=tk.DISABLED,          # initially disabled until round starts
    command=lambda: set_choice(0)
)
paper_btn = tk.Button(
    button_frame,
    text="PAPER",
    width=10,
    height=2,
    state=tk.DISABLED,
    command=lambda: set_choice(1)
)
scissors_btn = tk.Button(
    button_frame,
    text="SCISSORS",
    width=10,
    height=2,
    state=tk.DISABLED,
    command=lambda: set_choice(2)
)

rock_btn.grid(row=0, column=0, padx=10, pady=5)
paper_btn.grid(row=0, column=1, padx=10, pady=5)
scissors_btn.grid(row=0, column=2, padx=10, pady=5)

# =========================
# "Play Again / Start Round" button
# =========================

again_frame = tk.Frame(root)
again_frame.pack(pady=20)

again_btn = tk.Button(
    again_frame,
    text="Play Again / Start Round",
    width=20,
    height=2,
    command=start_round
)
again_btn.pack()

# On launch: show idle state
reset_round()

# Start the Tk event loop
root.mainloop()
