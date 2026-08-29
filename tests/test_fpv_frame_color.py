"""Locks in the color-channel invariant the FPV frame path depends on.

The simulator captures the framebuffer as RGB (cv2.COLOR_RGBA2RGB), the
command server ships it as a PNG via cv2.imencode, and the client rebuilds it
with cv2.imdecode and hands it back *without* any further color conversion
(tello_sim_client.TelloSimClient.get_frame_read).

That is only correct because the encode and decode are BOTH OpenCV: imencode
treats its input array as BGR and writes a standard RGB PNG (swapping channels
internally), and imdecode reads that RGB PNG straight back into a BGR array
(swapping again). The two swaps cancel, so the imencode -> imdecode round trip
is an *identity on the array bytes* no matter what the channels actually mean.
It is the pairing that makes it channel-agnostic, not imdecode on its own
(which is indeed BGR-by-convention in isolation).

This module proves that empirically, with no test framework required:

    python tests/test_fpv_frame_color.py

It is also plain-`pytest` discoverable if the repo adopts one later.
"""
import numpy as np
import cv2


def _sim_capture_rgb(rgba: np.ndarray) -> np.ndarray:
    """Simulator's capture conversion (ursina_adapter._tick_impl)."""
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB)


def _png_roundtrip(frame: np.ndarray) -> np.ndarray:
    """Server encode (command_server get_latest_frame) + client decode."""
    ok, buffer = cv2.imencode(".png", frame)
    assert ok, "cv2.imencode failed"
    return cv2.imdecode(np.frombuffer(buffer.tobytes(), np.uint8), cv2.IMREAD_COLOR)


def test_client_receives_rgb_without_conversion() -> None:
    """The frame the client decodes already equals the RGB the sim captured,
    so get_frame_read needs no client-side cvtColor."""
    rng = np.random.default_rng(0)
    rgba = rng.integers(0, 256, size=(360, 640, 4), dtype=np.uint8)
    rgba[:, :, 3] = 255  # opaque; the alpha channel is dropped on capture

    captured_rgb = _sim_capture_rgb(rgba)
    client_frame = _png_roundtrip(captured_rgb)

    assert np.array_equal(client_frame, captured_rgb)


def test_new_pipeline_is_byte_identical_to_old() -> None:
    """The RGB output handed to callers is byte-identical to the previous
    BGR-capture + client BGR2RGB pipeline — same frames, one fewer conversion."""
    rng = np.random.default_rng(1)
    rgba = rng.integers(0, 256, size=(360, 640, 4), dtype=np.uint8)
    rgba[:, :, 3] = 255

    # Old: capture BGR, PNG round trip, then client converts BGR -> RGB.
    old = cv2.cvtColor(_png_roundtrip(cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)),
                       cv2.COLOR_BGR2RGB)
    # New: capture RGB, PNG round trip, client returns it as-is.
    new = _png_roundtrip(cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB))

    assert np.array_equal(old, new)


if __name__ == "__main__":
    test_client_receives_rgb_without_conversion()
    test_new_pipeline_is_byte_identical_to_old()
    print("OK: FPV frame color round-trip invariants hold")
