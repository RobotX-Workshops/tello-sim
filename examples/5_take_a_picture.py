import os
import cv2
import time
import numpy as np
from tello_sim.tello_sim_client import TelloSimClient

# Initialize and connect
tello = TelloSimClient()
tello.connect()
tello.streamon()

# Takeoff
tello.takeoff()
time.sleep(5)  # Let drone stabilize after takeoff

# Get frame object
frame_read = tello.get_frame_read()

tello.streamoff()

# Prepare directory to save
script_dir = os.path.dirname(__file__)
artifact_folder_path = os.path.join(script_dir, "../artifacts/images")
os.makedirs(artifact_folder_path, exist_ok=True)

print("[Example] Saving captured picture to:", artifact_folder_path)

# Save the frame
save_path = os.path.join(artifact_folder_path, "picture.png")
cv2.imwrite(save_path, np.array(frame_read.frame))



# Land
tello.land()