# Tello Drone Sim

This is a simple simulation of a Tello drone using Ursina. The drone can be controlled via tcp calls.

in the repo there is the simulation server along with a client class that can be used to interact with the sim server

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

5. Run the program by running:

```bash
python tello_drone.py
```

## Running the simulation

To run the simulation, run the following command:

```bash
python tello_sim/run_sim.py
```

