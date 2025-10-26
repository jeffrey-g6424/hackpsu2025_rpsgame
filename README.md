This project is essentially the Rock, Paper, Scissor program inspired from C project ideas from GeeksForGeeks. However, a camera is used to see player's hand gesture input (closed fist for rock, open hand for paper, and two fingers for scissors).

Assuming you've downloaded all the files and are running this in VS Code, put each step into Terminal and run:

# 1. Go to the project directory that contains:
#    - cam_rps.py   (the Python webcam controller)
#    - librps.dylib (the compiled C game logic as a dynamic library)
#    - rps.c / rps.h (your C source and header, for reference)
cd /path/to/your/project

# 2. Create a Python 3.12 virtual environment called "rpscam-env".
#    We do this because mediapipe only ships wheels (prebuilt binaries)
#    for certain Python versions, including 3.12. Using a venv keeps
#    those dependencies isolated from your system Python.
python3.12 -m venv rpscam-env

# 3. Activate the virtual environment.
#    After this, `python` and `pip` will point to the versions inside
#    rpscam-env instead of your global Python install.
source rpscam-env/bin/activate

# 4. (Optional sanity check) Show the active Python / pip version.
#    You should now see Python 3.12.x here.
python --version
pip --version

# 5. Upgrade pip inside the virtual environment to the latest installer.
#    This helps avoid install issues with newer wheels.
pip install --upgrade pip

# 6. Install required Python packages for the camera game:
#    - opencv-python: access the webcam, draw the UI overlay
#    - mediapipe: hand landmark detection (to read ROCK/PAPER/SCISSORS from your hand)
pip install opencv-python mediapipe

# 7. Run the camera-based Rock/Paper/Scissors game.
#    cam_rps.py will:
#      - open your webcam
#      - detect your hand pose (fist / open hand / peace sign)
#      - convert that gesture to ROCK, PAPER, or SCISSORS
#      - call into the C library (librps.dylib) using ctypes
#      - display the result of the round
python cam_rps.py
