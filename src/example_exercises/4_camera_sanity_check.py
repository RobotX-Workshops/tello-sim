from djitellopy import Tello
import cv2

# Create a Tello instance
tello = Tello()

# Connect to Tello
tello.connect()

tello.streamon()

try:
    while True:
        img = tello.get_frame_read().frame
        if img is not None:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            cv2.imshow("frame", img)
        cv2.waitKey(1)
except KeyboardInterrupt:
    exit(1)
finally:
    print("fin")
