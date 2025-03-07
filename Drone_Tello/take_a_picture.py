import os
import cv2
import time
from tello_client import TelloSimClient

# Create a Tello instance
tello = TelloSimClient()

# Connect to the simulation
tello.connect()
tello.streamon()


# Takeoff
tello.takeoff()
time.sleep(5)  # Wait for stable hover

# Ensure artifact folder exists
script_dir = os.path.dirname(__file__)
artifact_folder_path = os.path.join(script_dir, "../../artifacts/images")
os.makedirs(artifact_folder_path, exist_ok=True)

# Capture frame via simulation
tello.capture_frame()

# Get the latest frame from the simulation
img = tello.get_frame()
if img is not None:
    save_path = os.path.join(artifact_folder_path, "picture.png")
    cv2.imwrite(save_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(f"Image saved to {save_path}")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("No image captured.")

# Land the drone
tello.land()

print("Mission complete.")
