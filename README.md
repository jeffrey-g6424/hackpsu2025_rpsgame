This project is essentially the Rock, Paper, Scissor program inspired from C project ideas from GeeksForGeeks. However, a camera is used to see player's hand gesture input (closed fist for rock, open hand for paper, and two fingers for scissors).

Assuming you've downloaded all the files and are running this in VS Code, follow the below steps:

1. Go to the project directory that contains:
 - cam_rps.py
 - librps.dylib
 - rps.c / rps.h


2. Create a Python 3.12 virtual environment called "rpscam-env" Need to install Python version 3.12.x if necessary.

   Run this in Terminal: python3.12 -m venv rpscam-env
   

3. Activate the virtual environment.

   Run this in Terminal: source rpscam-env/bin/activate

   
4. Upgrade pip inside the virtual environment to the latest installer. This helps avoid install issues with newer wheels.

   Run this in Terminal: pip install --upgrade pip


5. Install required Python packages for the camera game:
 - opencv-python: access the webcam, draw the UI overlay
 - mediapipe: hand landmark detection (to read ROCK/PAPER/SCISSORS from your hand)
 
   Run this in Terminal: pip install opencv-python mediapipe

   
6. Run the camera-based Rock/Paper/Scissors game.
  cam_rps.py will:
  - open your webcam
  - detect your hand pose (fist / open hand / peace sign)
  - convert that gesture to ROCK, PAPER, or SCISSORS
  - call into the C library (librps.dylib) using ctypes
  - display the result of the round
    
    Run the following in Terminal depending on which version you'd like to play:
    - For game only in Terminal (no camera): ./rps_cli
    - For game with a simple GUI (no camera): python3 ui.py
    - For game with the camera: python3 new_rps_with_cam_and_gui.py

******
