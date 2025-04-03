# Tello Drone Sim

This is a simple simulation of a Tello drone using Ursina. The drone can be controlled via tcp calls.

In the repo there is the simulation server along with a client class that can be used to interact with the sim server

![Features](./images/Features.gif)

## Setup

1. Create the virtual environment by running:

```bash
python3 -m venv venv
```

2. Activate the virtual environment by running:

```bash
source venv/bin/activate
```

3. Install the required packages by running:

```bash
pip install -r requirements.txt
```

4. Export the python path by running:

```bash
export PYTHONPATH=$PWD
```


## Running the simulation

To run the simulation, run the following command:

```bash
python tello_sim/run_sim.py
```

You can try running some of the [examples](./examples) to see how the simulation works. The examples are located in the `examples` folder. 

Or use the [client](./tello_sim/tello_sim_client.py) class to interact with the simulation server. The client class is located in the `tello_sim` folder.