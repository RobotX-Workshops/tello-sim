from tello_sim.tello_drone_sim import TelloDroneSim


sim = TelloDroneSim()
        
def update():
    """
    This function must be global and is called every frame by Ursina.
    """
    sim.update()
    

sim.start()
