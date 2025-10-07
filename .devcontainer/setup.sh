#!/bin/bash

# Tello Simulator Dev Container Setup Script
# This script generates a platform-specific devcontainer.json from the template

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/devcontainer.template.json"
OUTPUT_FILE="$SCRIPT_DIR/devcontainer.json"

echo "🚁 Tello Simulator Dev Container Setup"
echo "====================================="

# Function to detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            if grep -q Microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Function to configure for macOS
configure_macos() {
    local platform="macOS"
    local dockerfile_suffix=""
    local run_args='[
		"--env", "DISPLAY=host.docker.internal:0"
	]'
    local mounts='[]'
    local post_create_command="echo 'macOS setup complete. Install XQuartz and run: xhost +localhost'"
    
    echo "📱 Configuring for macOS..."
    echo "   - Using host.docker.internal for DISPLAY"
    echo "   - No X11 socket mounting (not available on macOS)"
    echo "   - Requires XQuartz for GUI support"
    
    generate_config "$platform" "$dockerfile_suffix" "$run_args" "$mounts" "$post_create_command"
}

# Function to configure for Linux
configure_linux() {
    local platform="Linux"
    local dockerfile_suffix=""
    local run_args='[
		"--env", "DISPLAY=${localEnv:DISPLAY:unix:0}",
		"--network", "host"
	]'
    local mounts='[
		"source=/tmp/.X11-unix,target=/tmp/.X11-unix,type=bind"
	]'
    local post_create_command="echo 'Linux setup complete. X11 forwarding configured.'"
    
    echo "🐧 Configuring for Linux..."
    echo "   - Using X11 socket mounting"
    echo "   - Host networking enabled"
    echo "   - Direct DISPLAY forwarding"
    
    generate_config "$platform" "$dockerfile_suffix" "$run_args" "$mounts" "$post_create_command"
}

# Function to configure for Windows/WSL
configure_windows() {
    local platform="Windows"
    local dockerfile_suffix=".windows"
    local run_args='[
		"--env", "DISPLAY=:1"
	]'
    local mounts='[]'
    local post_create_command=".devcontainer/setup-windows.sh"
    
    echo "🪟 Configuring for Windows..."
    echo "   - Using VNC server on port 5901"
    echo "   - Virtual framebuffer display"
    echo "   - GUI accessible via VNC viewer or browser"
    
    generate_config "$platform" "$dockerfile_suffix" "$run_args" "$mounts" "$post_create_command"
}

# Function to configure for WSL
configure_wsl() {
    echo "🪟🐧 WSL detected. Choose your preferred setup:"
    echo "1) WSL with X11 forwarding (requires Windows X server)"
    echo "2) VNC server (works without additional setup)"
    echo "3) Linux-style (if you have X11 forwarding configured)"
    
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            local platform="WSL (X11)"
            local dockerfile_suffix=""
            local run_args='[
				"--env", "DISPLAY=host.docker.internal:0"
			]'
            local mounts='[]'
            local post_create_command="echo 'WSL X11 setup complete. Ensure Windows X server is running.'"
            
            echo "   - Using Windows X server forwarding"
            echo "   - Requires VcXsrv, Xming, or similar on Windows"
            ;;
        2)
            configure_windows
            return
            ;;
        3)
            configure_linux
            return
            ;;
        *)
            echo "❌ Invalid choice. Using VNC server setup."
            configure_windows
            return
            ;;
    esac
    
    generate_config "$platform" "$dockerfile_suffix" "$run_args" "$mounts" "$post_create_command"
}

# Function to generate the final config
generate_config() {
    local platform="$1"
    local dockerfile_suffix="$2"
    local run_args="$3"
    local mounts="$4"
    local post_create_command="$5"
    
    # Read template and substitute variables (escape forward slashes for sed)
    local escaped_post_create=$(echo "$post_create_command" | sed 's/\//\\\//g')
    sed -e "s/\${PLATFORM}/$platform/g" \
        -e "s/\${DOCKERFILE_SUFFIX}/$dockerfile_suffix/g" \
        -e "s/\${POST_CREATE_COMMAND}/$escaped_post_create/g" \
        "$TEMPLATE_FILE" > "$OUTPUT_FILE.tmp"
    
    # Replace JSON arrays (more complex substitution)
    python3 -c "
import json
import sys

# Read the template with placeholders
with open('$OUTPUT_FILE.tmp', 'r') as f:
    content = f.read()

# Replace the JSON array placeholders
run_args = $run_args
mounts = $mounts

content = content.replace('\${RUN_ARGS}', json.dumps(run_args, indent=1).replace('\n', '\n\t'))
content = content.replace('\${MOUNTS}', json.dumps(mounts, indent=1).replace('\n', '\n\t'))

# Write the final file
with open('$OUTPUT_FILE', 'w') as f:
    f.write(content)

# Validate JSON
try:
    with open('$OUTPUT_FILE', 'r') as f:
        json.load(f)
    print('✅ Generated valid devcontainer.json')
except json.JSONDecodeError as e:
    print(f'❌ Invalid JSON generated: {e}')
    sys.exit(1)
"
    
    # Clean up temp file
    rm "$OUTPUT_FILE.tmp"
    
    echo "✅ devcontainer.json generated for $platform"
}

# Function to show usage instructions
show_usage_instructions() {
    local platform="$1"
    
    echo ""
    echo "📋 Next Steps:"
    echo "=============="
    
    case "$platform" in
        "macos")
            echo "1. Install XQuartz: brew install --cask xquartz"
            echo "2. Start XQuartz and enable 'Allow connections from network clients'"
            echo "3. Run: xhost +localhost"
            echo "4. Restart VS Code and 'Reopen in Container'"
            ;;
        "linux")
            echo "1. Ensure X11 forwarding is enabled"
            echo "2. Restart VS Code and 'Reopen in Container'"
            echo "3. Test with: python -c \"import tkinter; tkinter.Tk().mainloop()\""
            ;;
        "windows"|"WSL"*)
            echo "1. Restart VS Code and 'Reopen in Container'"
            echo "2. Connect to VNC server at: http://localhost:5901"
            echo "3. VNC password: vncpass"
            echo "4. Or use VNC viewer: localhost:5901"
            ;;
    esac
    
    echo ""
    echo "🚁 Ready to run Tello Simulator!"
    echo "   python tello_sim/run_sim.py"
}

# Main execution
main() {
    # Check if template exists
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        echo "❌ Template file not found: $TEMPLATE_FILE"
        exit 1
    fi
    
    # Auto-detect platform or allow override
    if [[ $# -eq 0 ]]; then
        PLATFORM=$(detect_platform)
        echo "🔍 Auto-detected platform: $PLATFORM"
    else
        PLATFORM="$1"
        echo "🎯 Using specified platform: $PLATFORM"
    fi
    
    # Configure based on platform
    case "$PLATFORM" in
        "macos")
            configure_macos
            show_usage_instructions "macos"
            ;;
        "linux")
            configure_linux
            show_usage_instructions "linux"
            ;;
        "windows")
            configure_windows
            show_usage_instructions "windows"
            ;;
        "wsl")
            configure_wsl
            show_usage_instructions "WSL"
            ;;
        *)
            echo "❌ Unsupported platform: $PLATFORM"
            echo "Supported platforms: macos, linux, windows, wsl"
            echo "Usage: $0 [platform]"
            exit 1
            ;;
    esac
    
    echo ""
    echo "🎉 Setup complete! Your devcontainer.json is ready."
}

# Run main function
main "$@"