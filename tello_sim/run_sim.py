import logging
import os

from tello_drone_sim import TelloDroneSim

# Per-command/per-frame chatter is logged at DEBUG level and hidden by
# default; set TELLO_SIM_DEBUG=1 to see it.
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("TELLO_SIM_DEBUG") else logging.INFO,
    format="%(message)s",
)

sim = TelloDroneSim()
        
def update():
    """
    This function must be global and is called every frame by Ursina.
    """
    sim.update()
    

sim.start()
