#!/bin/bash

# Windows Dev Container Setup Script
# This script helps set up the development environment for Windows users

echo "=== Tello Simulator - Windows Dev Container Setup ==="

# Check if we're running in a container
if [ -f /.dockerenv ]; then
    echo "✅ Running inside Docker container"
    
    # Install Python requirements
    if [ -f "/workspaces/tello-sim/requirements.txt" ]; then
        echo "📦 Installing Python requirements..."
        pip install -r /workspaces/tello-sim/requirements.txt
    fi
    
    # Test GUI support
    echo "🖥️ Testing GUI support..."
    python3 -c "
import tkinter as tk
import sys
try:
    root = tk.Tk()
    root.title('GUI Test - Tello Simulator')
    tk.Label(root, text='✅ GUI Support Working!\\nClose this window to continue.').pack(pady=20)
    root.geometry('300x100')
    root.after(3000, root.destroy)  # Auto-close after 3 seconds
    root.mainloop()
    print('✅ GUI test successful!')
except Exception as e:
    print(f'❌ GUI test failed: {e}')
    sys.exit(1)
"
    
    echo "🚁 Setup complete! You can now run the Tello simulator."
    echo "📺 VNC server is running on port 5901 (password: vncpass)"
    echo "🌐 Access via browser: http://localhost:5901"
    
else
    echo "⚠️ This script should be run inside the dev container."
    echo "Please open this project in VS Code and use 'Reopen in Container'."
fi