"""TCP transport shared by TelloSimClient and SimulatorClient.

Both clients talk to the same simulator command server
(tello_sim/command_server.py) on the same port, so the wire protocol lives
here rather than being duplicated in each of them. This is the only module
on the client side that touches the TCP command channel.
"""
import socket


class SimConnection:
    """Request/response plumbing for one simulator host:port.

    Every call opens a fresh connection: the server handles exactly one
    command per connection and then closes it (see
    tello_sim/command_server.py:_handle_connection).
    """

    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port

    def is_reachable(self, timeout=1.0) -> bool:
        """True if the simulator's command server accepts a connection."""
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except OSError:
            # ConnectionRefusedError and socket.timeout are both OSError
            # subclasses, so this one clause covers every failure mode.
            return False

    def send(self, command: str) -> None:
        """Fire-and-forget a command that produces no reply."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())
        except ConnectionRefusedError:
            print(f"[Error] Unable to connect to the simulation at {self.host}:{self.port}")

    def request(self, command: str) -> str:
        """Send a command and return its reply, or "N/A" if unreachable."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())
                # The server sends one response and closes the connection, so
                # read until EOF. A single recv() can return a truncated
                # payload when TCP splits a larger JSON response (get_state /
                # get_position), yielding intermittent parse failures.
                chunks = []
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                return b''.join(chunks).decode()
        except ConnectionRefusedError:
            print(f"[Error] Unable to retrieve '{command}' from {self.host}:{self.port}")
            return "N/A"

    def request_framed(self, command: str) -> bytes | None:
        """Send a command whose reply is a 4-byte big-endian length + payload.

        Used by the frame channel (get_latest_frame). Returns None when the
        server reports no frame (length 0) or the transfer fails.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())

                # Receive frame size (4 bytes)
                size_data = s.recv(4)
                if len(size_data) != 4:
                    print("[Error] Failed to receive frame size")
                    return None

                frame_size = int.from_bytes(size_data, byteorder='big')

                # If size is 0, no frame available
                if frame_size == 0:
                    print("[Debug] No frame available from simulator")
                    return None

                # Receive the frame data
                frame_data = b''
                bytes_received = 0
                while bytes_received < frame_size:
                    chunk = s.recv(min(4096, frame_size - bytes_received))
                    if not chunk:
                        break
                    frame_data += chunk
                    bytes_received += len(chunk)

                if len(frame_data) != frame_size:
                    print("[Error] Incomplete frame data")
                    return None
                return frame_data

        except ConnectionRefusedError:
            print(f"[Error] Unable to connect to the simulation at {self.host}:{self.port}")
            return None
        except Exception as e:
            print(f"[Error] Failed to get frame: {e}")
            return None
