import os
from threading import Thread
import time
from typing import cast
from djitellopy import Tello
import cv2

# The frame rate for the video
FPS = 30

tello = Tello()
tello.connect()
keepRecording = True
tello.streamon()

frame_read = tello.get_frame_read()

script_dir = os.path.dirname(__file__)
# The folder where the images will be stored
images_folder_path = os.path.join(script_dir, "../../artifacts/videos")
os.makedirs(images_folder_path, exist_ok=True)

# The path for the output video file
video_file_path = os.path.join(script_dir, "../../artifacts/videos/video.mp4")
os.makedirs(os.path.dirname(video_file_path), exist_ok=True)


def capture_images():
    frame_count = 0
    while keepRecording:
        frame = cast(cv2.typing.MatLike, frame_read.frame)
        image_file_path = os.path.join(
            images_folder_path, f"frame_{frame_count:04d}.jpg"
        )
        cv2.imwrite(image_file_path, frame)
        frame_count += 1
        time.sleep(1 / FPS)

    print("Finished capturing images")


# Run the image capture in a separate thread
recorder = Thread(target=capture_images)
recorder.start()

tello.takeoff()
tello.move_up(50)
tello.rotate_counter_clockwise(360)
tello.land()

keepRecording = False
recorder.join()

# Create the video from the captured images
frame = cast(cv2.typing.MatLike, frame_read.frame)
height, width, _ = frame.shape
fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore
video = cv2.VideoWriter(video_file_path, fourcc, FPS, (width, height), True)

for frame_count in range(len(os.listdir(images_folder_path))):
    image_file_path = os.path.join(images_folder_path, f"frame_{frame_count:04d}.jpg")
    frame = cv2.imread(image_file_path)
    video.write(frame)

print("Finished creating video")
video.release()
