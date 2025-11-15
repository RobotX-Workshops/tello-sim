# Tello Drone Sim

This is a simple simulation of a Tello drone using Ursina. The drone can be controlled via tcp calls.

In the repo there is the simulation server along with a client class that can be used to interact with the sim server

![Features](./images/Features.gif)

## Setup

### Option 1: Dev Container (Recommended)

The easiest way to get started is using the provided dev container which includes all dependencies and GUI support:

1. **Setup the dev container for your platform:**

   ```bash
   .devcontainer/setup.sh
   ```

   This will auto-detect your platform (macOS, Linux, Windows, WSL) and generate the appropriate `devcontainer.json`.

2. **Open in VS Code:**
   - Install the "Dev Containers" extension
   - Open Command Palette (Cmd/Ctrl + Shift + P)
   - Run "Dev Containers: Reopen in Container"

3. **Platform-specific requirements:**
   - **macOS**: Install XQuartz (`brew install --cask xquartz`) and run `xhost +localhost`
   - **Linux**: X11 forwarding should work out of the box
   - **Windows**: Access GUI via VNC at `http://localhost:5901` (password: `vncpass`)

### Option 2: Manual Setup

If you prefer to set up the environment manually:

1. Create the virtual environment by running:

   ```bash
   python3.12 -m venv venv
   ```

2. Activate the virtual environment by running:

   ```bash
   source venv/bin/activate
   ```

3. Install the required packages by running:

   ```bash
   pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
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

## Troubleshooting

- For a specific python version on macOS, consider using [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv) to manage multiple python versions. 