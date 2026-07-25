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

Or use the [client](./tello_sim_client.py) class to interact with the simulation server. The client class is located in the `tello_sim` folder.

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
