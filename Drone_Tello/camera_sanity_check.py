from tello_client import TelloConnector
import cv2

# Desired window size
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 360

# Create a Tello instance
tello = TelloConnector()

# Connect to Tello
tello.connect()

tello.streamon()

# Create a normal, resizable window
cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
cv2.resizeWindow("frame", WINDOW_WIDTH, WINDOW_HEIGHT)

try:
    while True:
        img = tello.get_frame()
        if img is not None:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            # Resize the image to fit the window size
            img_resized = cv2.resize(img_bgr, (WINDOW_WIDTH, WINDOW_HEIGHT), interpolation=cv2.INTER_AREA)
            cv2.imshow("frame", img_resized)
        if cv2.waitKey(1) == ord('q'):
            break
except KeyboardInterrupt:
    pass
finally:
    print("fin")
    cv2.destroyAllWindows()
