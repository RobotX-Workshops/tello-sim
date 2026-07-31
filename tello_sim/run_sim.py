import logging
import os

from tello_drone_sim import TelloDroneSim

# Per-command/per-frame chatter is logged at DEBUG level and hidden by
# default; set TELLO_SIM_DEBUG=1 to see it.
logging.basicConfig(
    level=logging.DEBUG
    if os.environ.get("TELLO_SIM_DEBUG", "").lower() in ("1", "true", "yes")
    else logging.INFO,
    format="%(message)s",
)

sim = TelloDroneSim()
        
def update():
    """
    This function must be global and is called every frame by Ursina.
    """
    sim.update()


def input(key):  # noqa: A001 - Ursina looks up __main__.input by this exact name
    """
    This function must be global and is called by Ursina on every key press.
    """
    sim.input(key)


sim.start()
