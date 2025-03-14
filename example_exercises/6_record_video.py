import os
from threading import Thread
import time
from typing import cast
from tello_sim.tello_sim_client import TelloSimClient

import cv2

# Configuration
FPS = 30

# Initialize Tello connector
tello = TelloSimClient()
tello.connect()

tello.streamon()
time.sleep(2)
# Define paths to save inside tello_recording
recording_folder = os.path.join(os.getcwd(), "tello_recording")
images_folder_path = os.path.join(recording_folder, "frames")
video_file_path = os.path.join(recording_folder, "video.mp4")
os.makedirs(images_folder_path, exist_ok=True)

# Recording control
keep_recording = True


def capture_images():
    frame_count = 0
    while keep_recording:
        frame = tello.get_frame_read().frame
        if frame is not None:
            image_file_path = os.path.join(images_folder_path, f"frame_{frame_count:04d}.jpg")
            cv2.imwrite(image_file_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            frame_count += 1
            print(f"[Capture] Saved frame {frame_count}")
        else:
            print("[Capture] No frame received.")
        time.sleep(1 / FPS)

    print("[Capture] Finished capturing frames.")


# Start recording thread
recorder_thread = Thread(target=capture_images)
recorder_thread.start()

# Drone mission
tello.takeoff()
time.sleep(5)
tello.move_up(50)
time.sleep(5)
tello.rotate_counter_clockwise(360)
time.sleep(5)
tello.land()

# Stop recording
keep_recording = False
recorder_thread.join()

# Create video from frames
frame_files = sorted(os.listdir(images_folder_path))
if frame_files:
    first_frame = cv2.imread(os.path.join(images_folder_path, frame_files[0]))
    height, width, _ = first_frame.shape

    video_writer = cv2.VideoWriter(
        video_file_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (width, height)
    )

    for frame_file in frame_files:
        frame_path = os.path.join(images_folder_path, frame_file)
        frame = cv2.imread(frame_path)
        video_writer.write(frame)

    video_writer.release()
    print(f"[Video] Video saved at {video_file_path}")
else:
    print("[Video] No frames captured. Video not created.")

print("Finished creating video")