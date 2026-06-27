import os
import cv2
from src.utils.logger import logger

ADMIN_FACE_DIR = "C:/Users/MMM JAVID/Desktop/Advance_Voice_Assistant/data/admin_face"
ADMIN_FACE_PATH = os.path.join(ADMIN_FACE_DIR, "admin.jpg")
TEMP_FACE_PATH  = "data/WIN_20260623_02_27_10_Pro.jpg"

MODEL_NAME      = "ArcFace"
DETECTOR        = "opencv"
MAX_ATTEMPTS    = 15

def register_admin_face() -> None:

    os.makedirs(ADMIN_FACE_DIR, exist_ok=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam for face registration.")

    logger.info("Face registration: look at the camera. Press SPACE to capture, ESC to cancel.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Register admin face — SPACE to capture, ESC to cancel", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 32:
            cv2.imwrite(ADMIN_FACE_PATH, frame)
            logger.info(f"Admin face saved: {ADMIN_FACE_PATH}")
            break
        elif key == 27:
            logger.info("Face registration cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()

def verify_admin_face() -> bool:

    if not os.path.exists(ADMIN_FACE_PATH):
        logger.error(
            "No admin face registered. Run: python scripts/register_face.py"
        )
        return False

    try:
        from deepface import DeepFace
    except ImportError:
        logger.error("deepface not installed. Run: pip install deepface opencv-python tf-keras")
        return False

    os.makedirs("data", exist_ok=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam for face verification.")
        return False

    logger.info("Face verification: looking at camera...")
    verified = False

    for attempt in range(MAX_ATTEMPTS):
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imwrite(TEMP_FACE_PATH, frame)

        try:
            result = DeepFace.verify(
                img1_path=TEMP_FACE_PATH,
                img2_path=ADMIN_FACE_PATH,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR,
                enforce_detection=True,
                silent=True,
            )

            if result.get("verified",False):
                logger.info(
                    f"Admin verified on attempt {attempt + 1}. "
                    f"Distance: {result.get('distance', '?'):.4f}"
                )
                verified = True
                break
            else:
                logger.debug(f"Attempt {attempt + 1}: face present but no match.")

        except Exception as e:

            logger.debug(f"Attempt {attempt + 1}: {e}")
            continue

    cap.release()

    if os.path.exists(TEMP_FACE_PATH):
        os.remove(TEMP_FACE_PATH)

    if not verified:
        logger.warning("Face verification failed after all attempts.")

    return verified

