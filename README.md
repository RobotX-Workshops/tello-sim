# Tello Drone Sim

This is a simple simulation of a Tello drone using Ursina. The drone can be controlled via tcp calls.

In the repo there is the simulation server along with a client class that can be used to interact with the sim server

![Features](./images/Features.gif)

## Setup

### Option 1: Dev Container (Recommended)

The easiest way to get started is using the provided dev container, which sets up GUI/X11/VNC support for you:

1. **Setup the dev container for your platform:**

   ```bash
   .devcontainer/setup.sh
   ```

   This will auto-detect your platform (macOS, Linux, Windows, WSL) and generate the appropriate `devcontainer.json`.

2. **Open in VS Code:**
   - Install the "Dev Containers" extension
   - Open Command Palette (Cmd/Ctrl + Shift + P)
   - Run "Dev Containers: Reopen in Container"

3. **Install the Python dependencies (macOS/Linux only — the Windows config does this for you automatically via `setup-windows.sh`):**

   ```bash
   pip install -r requirements.txt
   export PYTHONPATH=$PWD
   ```

4. **Platform-specific requirements:**
   - **macOS**: Install XQuartz (`brew install --cask xquartz`) and run `xhost +localhost`
   - **Linux**: X11 forwarding should work out of the box
   - **Windows**: Access GUI via VNC at `http://localhost:5901` (password: `vncpass`)

### Option 2: Manual Setup

If you prefer to set up the environment manually:

1. Create the virtual environment by running:

   ```bash
   python3.12 -m venv --copies venv
   ```

   `--copies` copies the interpreter into the venv instead of symlinking it. Without it, a Homebrew/pyenv upgrade that removes the Python version you built the venv from leaves the venv silently broken (see [Troubleshooting](#troubleshooting)).

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

Or use the [client](./tello_sim_client.py) class to interact with the simulation server. `tello_sim_client.py` lives in the repo root; the simulator server code lives in the `tello_sim` folder.

## Position & telemetry API

The simulator exposes the drone's position and state two ways — poll it on
demand, or subscribe to a push stream:

- **Poll (TCP port 9999):** the commands `get_position` and `get_state` return
  JSON. Via the client:

  ```python
  tello.get_position()  # {'x': -1.54, 'y': 0.2, 'z': 0.5, 'yaw': 0.0}
  tello.get_state()     # position + pitch/roll/speeds/battery/flying/time
  ```

- **Subscribe (UDP port 9998):** send the datagram `subscribe` and the
  simulator pushes the same JSON state at ~10 Hz until you send `unsubscribe`
  (or stop resubscribing for 10 s). Via the client:

  ```python
  tello.subscribe_state(lambda state: print(state["x"], state["z"]))
  ...
  tello.unsubscribe_state()
  ```

`x`/`z` are metres in the simulator's world frame, `y` is height above the
ground in metres (matching `get_height`), and `yaw` is degrees in [-180, 180].
See [examples/15_position_telemetry.py](./examples/15_position_telemetry.py).

## Troubleshooting

### `ModuleNotFoundError: No module named 'ursina'` even with the venv activated

The venv's interpreter is probably a dangling symlink. Venvs created without `--copies` symlink `venv/bin/python` to the Python they were built from (e.g. `/opt/homebrew/opt/python@3.12/...`); if Homebrew later removes that version (`brew upgrade` / `brew cleanup`), the symlink dies. Your prompt still shows `(venv)`, but the shell skips the dead symlink during PATH lookup and falls through to some other Python (e.g. conda `base`) that doesn't have the packages — so imports fail no matter what you do with `PYTHONPATH`.

Diagnose it:

```bash
venv/bin/python --version   # "no such file or directory" => venv is dead
which python                # points outside venv/ despite (venv) prompt => same problem
```

Fix: recreate the venv against a Python that exists, using `--copies` so it can't happen again:

```bash
rm -rf venv
python3.12 -m venv --copies venv
source venv/bin/activate
venv/bin/python -m pip install -r requirements.txt
```

### `numpy` install failure inside the dev container

The dev container images (`.devcontainer/Dockerfile`, `.devcontainer/Dockerfile.windows`) are currently pinned to Python 3.9, while `requirements.txt` pins `numpy==2.2.3`, which does not publish wheels for Python 3.9 (2.0.2 is the newest 3.9-compatible release). If `pip install -r requirements.txt` fails inside the dev container with a "no matching distribution" error for `numpy`, this version mismatch is why — use the manual setup with Python 3.12 instead, or downgrade the `numpy` pin, until the container images are updated.

### Managing python versions

- For a specific python version on macOS, consider using [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv) to manage multiple python versions.
- Another alternative for macOS users is to use [Homebrew](https://brew.sh/) to install the desired python version:

  ```bash
  brew install python@3.12
  ```

- Conda users can create an environment with the desired python version:

  ```bash
  conda create -n tello-sim python=3.12
  conda activate tello-sim
  pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
  export PYTHONPATH=$PWD
  ```
