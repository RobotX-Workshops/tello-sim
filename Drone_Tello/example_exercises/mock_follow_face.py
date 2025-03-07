"""
This script is used to mock tracking a face in the frame and follow it with the drone.
Instead of the drones camera it uses the hosts computer camera to test functionality.
It prints the facetracking controller outputs but does not dispatch them to a drone
"""

import time
import cv2
from face_tracking.image_drawing_service import ImageDrawingService
from face_tracking.image_compression_service import ImageCompressionService
from face_tracking.recognition_face_identifier import RecognitionFaceIdentifier
from face_tracking.open_cv_wrapper import OpenCvWrapper
import logging
import argparse
from face_tracking.utils.positioning_utils import (
    get_box_center_xyz,
    get_distance_xyz,
    get_frame_center_xy,
    get_vector_xyz,
)
from src.controller_adapters.follow_face_controller import FaceFollowingController


args = argparse.ArgumentParser()

logging.basicConfig(level=logging.ERROR)

LOGGER = logging.getLogger(__name__)

# Variables
ZERO_DEPTH_BOX_SIZE = 400
DEPTH_TARGET = 650

open_cv = OpenCvWrapper()

image_compressor = ImageCompressionService(open_cv)

face_identifier = RecognitionFaceIdentifier(open_cv, image_compressor)

image_drawer = ImageDrawingService(open_cv)

controller = FaceFollowingController()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# tello.takeoff()
cam = open_cv.connect_to_camera()


while True:
    time.sleep(0.200)

    ret, frame = cam.read()

    if frame is None or frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
        LOGGER.debug("No frame")
        continue

    faces_trbl = face_identifier.identify_faces(frame)
    if not faces_trbl:
        LOGGER.debug("No faces")
        continue

    frame_center_xyz = (*get_frame_center_xy(frame), DEPTH_TARGET)

    closest = None
    for face_trbl in faces_trbl:
        box_center = get_box_center_xyz(face_trbl, DEPTH_TARGET)
        distance = get_distance_xyz(frame_center_xyz, box_center)
        if closest is None or distance < closest[1]:
            closest = (face_trbl, distance, box_center)
        frame = image_drawer.draw_box(
            frame,
            face_trbl,
            "green",
        )
        frame = image_drawer.draw_cross_hair_in_box(frame, face_trbl, 4, "green")

    assert closest is not None
    closest_box = closest[0]
    closest_distance = closest[1]
    closest_center = closest[2]

    vector_to_center = get_vector_xyz(frame_center_xyz, closest_center)

    frame = image_drawer.draw_box(frame, closest_box, "red")
    frame = image_drawer.draw_frame_center_cross_hair(frame, 2, 20, "red")

    LOGGER.debug(
        f"Closest face at {frame_center_xyz, closest_center} with distance {closest_distance}"
    )

    control_state = controller.get_state(vector_to_center)
    height, width = frame.shape[:2]
    bottom = height - 10
    left = 10

    # Write the control state information on the frame
    open_cv.write_text(
        frame,
        f"Forward: {control_state.forward_velocity},"
        f"Move Right: {control_state.right_velocity}, "
        f"Up: {control_state.up_velocity}, "
        f"Yaw Right: {control_state.yaw_right_velocity}",
        (left, bottom),
        cv2.FONT_HERSHEY_DUPLEX,
        0.5,  # Adjust the font scale as needed
        (255, 255, 255),
        1,
    )
    open_cv.show_image("frame", frame)

    # dispatcher.send_commands(control_state)

    if open_cv.listen_for_key(1) & 0xFF == ord("q"):
        break
