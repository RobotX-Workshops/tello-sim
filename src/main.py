

from tello_drone import DroneSimulator, TelloConnector
from ursina import *
from time import time, sleep

def update():
    if not drone_sim.tello.is_connected:
        return 
    if held_keys['shift']:
        if not drone_sim.tello.is_flying:
            drone_sim.tello.take_off()
        else:
            drone_sim.change_altitude("up")
    drone_sim.update_takeoff_indicator()
    if not drone_sim.tello.is_flying:
        drone_sim.camera_holder.position = drone_sim.drone.position + Vec3(0, 3, -7)
        
        return
    
    moving = False
    rolling = False
    
    if drone_sim.tello.stream_active:
        drone_sim.tello.capture_frame()
    
    if held_keys['w']:
        drone_sim.move("forward")
        moving = True
    if held_keys['s']:
        drone_sim.move("backward")
        moving = True
    if held_keys['a']:
        drone_sim.move("left")
        rolling = True
    if held_keys['d']:
        drone_sim.move("right")
        rolling = True
    if held_keys['j']:
        drone_sim.rotate(-drone_sim.rotation_speed)
    if held_keys['l']:
        drone_sim.rotate(drone_sim.rotation_speed)
    
    if held_keys['control']:
        drone_sim.change_altitude("down")
    if not moving:
        drone_sim.pitch_angle = 0  # Reset pitch when not moving
    
    if not rolling:
        drone_sim.roll_angle = 0  # Reset roll when not rolling
    

    drone_sim.update_movement()
    drone_sim.update_pitch_roll()



app = Ursina()
window.color = color.rgb(135, 206, 235)  
window.fullscreen = True
window.borderless = False
window.fps_counter.enabled = False  
window.render_mode = 'default'  


Sky(texture='sky_sunset')

tello_sim = TelloConnector()  
drone_sim = DroneSimulator(tello_sim)  # pass TelloSimulator to DroneSimulator
tello_sim.drone_sim = drone_sim
tello_sim.connect() 
def input(key):
    current_time = time()
    # Track keypress history for triple tap detection
    if key in tello_sim.last_keys:
        tello_sim.last_keys[key].append(current_time)
        tello_sim.last_keys[key] = [t for t in tello_sim.last_keys[key] if current_time - t < 0.8]  # Keep taps within 0.8 sec
    else:
        tello_sim.last_keys[key] = [current_time]

    # Detect triple tap
    if len(tello_sim.last_keys[key]) == 3:
        if key == 'w':
            tello_sim.flip_forward()
        elif key == 's':
            tello_sim.flip_back()
        elif key == 'a':
            tello_sim.flip_left()
        elif key == 'd':
            tello_sim.flip_right()
    
    if key == 'h':
        drone_sim.help_text.visible = not drone_sim.help_text.visible
    if key == 'c':
        drone_sim.toggle_camera_view()
    if key == 'v':  
        if tello_sim.stream_active:
            tello_sim.streamoff()
        else:
            tello_sim.streamon()
    if key == 'g':  
        tello_sim.land()
    if key == 'e':  
        tello_sim.emergency()
    if key == 'r':  
        print("Opening recorded frames folder...")
        tello_sim.get_frame_read()
    if key == '1':  
        tello_sim.set_speed(30)
    if key == '2':  
        tello_sim.set_speed(43.33)
    if key == '3':  
        tello_sim.set_speed(60)

app.run()