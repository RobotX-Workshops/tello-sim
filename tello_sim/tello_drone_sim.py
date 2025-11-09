from command_server import CommandServer
from ursina_adapter import UrsinaAdapter
import threading
import atexit
import signal
import sys

class TelloDroneSim:
    def __init__(self):
        self._ursina_adapter = UrsinaAdapter()
        self._server = CommandServer(self._ursina_adapter)
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle termination signals gracefully."""
        print("\n[Tello Sim] Received shutdown signal, cleaning up...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, '_server'):
            self._server.cleanup()

    @property
    def state(self):
        return self._ursina_adapter

    def start(self):
        # Check if port is available before starting
        if not self._server.check_port_available(9999):
            print("\n" + "="*70)
            print("ERROR: Cannot start simulator - Port 9999 is already in use!")
            print("="*70)
            print("\nAnother instance of the simulator may be running.")
            print("\nTo fix this, run one of these commands in your terminal:")
            print("  macOS/Linux: lsof -ti:9999 | xargs kill -9")
            print("  Windows:     netstat -ano | findstr :9999")
            print("               taskkill /PID <PID> /F")
            print("\nOr simply restart your computer.")
            print("="*70 + "\n")
            sys.exit(1)
        
        server_thread = threading.Thread(target=self._server.listen)
        server_thread.daemon = True
        server_thread.start()
        
        try:
            self._ursina_adapter.run()
        except KeyboardInterrupt:
            print("\n[Tello Sim] Interrupted, cleaning up...")
            self.cleanup()
        except Exception as e:
            print(f"[Tello Sim] Error: {e}")
            self.cleanup()
            raise

    def update(self) -> None:
        self._ursina_adapter.tick()