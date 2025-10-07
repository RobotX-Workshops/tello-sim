# Dev Container Template System

This directory contains a template-based dev container configuration system for the Tello Simulator project that automatically adapts to different platforms.

## Quick Start

Run the setup script to generate a platform-specific `devcontainer.json`:

```bash
.devcontainer/setup.sh
```

The script will:

1. 🔍 Auto-detect your platform (macOS, Linux, Windows, WSL)
2. 📝 Generate the appropriate `devcontainer.json` from the template
3. 📋 Show platform-specific setup instructions

## Files

- `devcontainer.template.json` - Template with platform variables
- `setup.sh` - Platform detection and configuration script
- `devcontainer.json` - Generated file (git-ignored)
- `Dockerfile` - Base Docker configuration
- `Dockerfile.windows` - Windows-specific Docker configuration with VNC
- `supervisord.conf` - Process manager for Windows VNC setup
- `setup-windows.sh` - Windows container initialization script

## Manual Platform Selection

You can also specify a platform manually:

```bash
.devcontainer/setup.sh macos     # Force macOS configuration
.devcontainer/setup.sh linux     # Force Linux configuration
.devcontainer/setup.sh windows   # Force Windows configuration
.devcontainer/setup.sh wsl       # WSL with options  
```

## Platform Configurations

### macOS

- ✅ Uses `host.docker.internal:0` for DISPLAY
- ❌ No X11 socket mounting (not available on macOS)
- 📦 Requires XQuartz: `brew install --cask xquartz`
- 🔧 Run `xhost +localhost` after XQuartz setup

### Linux

- ✅ Direct X11 socket mounting via `/tmp/.X11-unix`
- ✅ Host networking for optimal performance
- ✅ Uses local `$DISPLAY` environment variable
- 🚀 Works out of the box on most Linux distributions

### Windows

- 🖥️ VNC server on port 5901 (password: `vncpass`)
- 🌐 Web access: `http://localhost:5901`
- 📱 VNC client: `localhost:5901`
- 🎯 Virtual framebuffer with Fluxbox window manager

### WSL (Windows Subsystem for Linux)

Interactive setup with three options:

1. **X11 forwarding** - Requires Windows X server (VcXsrv, Xming)
2. **VNC server** - Same as Windows setup
3. **Linux-style** - If X11 forwarding already configured

## GUI Application Support

All configurations support GUI applications required by the Tello simulator's Ursina engine:

**Test GUI support:**

```bash
python -c "import tkinter; tkinter.Tk().mainloop()"
```

**Run the simulator:**

```bash
python tello_sim/run_sim.py
```

## Development Notes

- The generated `devcontainer.json` is git-ignored to prevent platform conflicts
- Each developer runs `setup.sh` once to configure for their environment
- Template uses JSON variable substitution via the setup script
- Windows configuration includes full VNC stack for GUI support

## Troubleshooting

**Script fails to detect platform:**

```bash
.devcontainer/setup.sh [platform]  # Specify manually
```

**GUI not working:**

- macOS: Ensure XQuartz is running and `xhost +localhost` was executed
- Linux: Check X11 forwarding with `echo $DISPLAY`
- Windows: Connect to VNC at `localhost:5901`

**Container won't start:**

- Check Docker is running
- Verify VS Code "Dev Containers" extension is installed
- Try "Dev Containers: Rebuild Container" from Command Palette
