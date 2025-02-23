from tello_drone_simulator import TelloDroneSimulator
from ursina import *

### TODO: Play with these to sort out the elements being outside the window
app = Ursina()
window.color = color.rgb(135, 206, 235)  
window.fullscreen = True

window.borderless = False 
window.fps_counter.enabled = False  
window.render_mode = 'default'  


Sky(texture='sky_sunset')

tello_sim = TelloDroneSimulator()  
drone_sim = TelloDroneSimulator(tello_sim)  

def input(key):
    if key == 'h':
        drone_sim.help_text.visible = not drone_sim.help_text.visible
    if key == 'c':
        drone_sim.toggle_camera_view()
def update():
    moving = False
    rolling = False

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
    if held_keys['shift']:
        drone_sim.change_altitude("up")
    if held_keys['control']:
        drone_sim.change_altitude("down")
    if not moving:
        drone_sim.pitch_angle = 0  # Reset pitch when not moving
    
    if not rolling:
        drone_sim.roll_angle = 0  # Reset roll when not rolling

    drone_sim.update_movement()
    drone_sim.update_pitch_roll()

app.run()
