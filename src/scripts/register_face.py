import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.utils.face_auth import register_admin_face

if __name__ == "__main__":
    print("=== JARVIS Admin Face Registration ===")
    print("Your face will be saved as the admin identity.")
    print("Make sure you are in good lighting and looking at the camera.\n")
    register_admin_face()
    print("\nDone! You can now use admin mode in JARVIS.")
    print("Say any admin command (e.g. 'uninstall AnyDesk') and JARVIS will verify your face.")