"""Scene editor — a separate window for moving gates and people.

This used to be an Ursina panel drawn inside the simulator window, but the FPV
path grabs the whole framebuffer (see UrsinaAdapter._tick_impl), so anything on
screen was burned into captured photos and video. Ursina/Panda3D owns exactly
one OS window, so a second window means a second process: this one is plain
Tkinter, driving the simulator over the same TCP command channel the client
libraries use.

    python tello_sim/run_sim.py     # the 3D window
    python tools/scene_editor.py    # this window

or `python run.py` to start both.

Edits apply live; "Save" persists them to gates.json and people.json.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk

# Run directly from tools/, so put the repo root on the path for the client.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator_client import SimulatorClient  # noqa: E402

# The simulator's command server handles one command per connection on a single
# accept loop, so an unthrottled slider drag would stall the render loop.
# Dirty values are coalesced and flushed at this interval instead.
FLUSH_INTERVAL_MS = 50
RECONNECT_INTERVAL_MS = 1000

# Editable fields per tab: (field, label, decimals). The min/max come from the
# simulator (get_scene()['ranges']) rather than being duplicated here.
GATE_FIELDS = [
    ('x', 'X (side)', 1),
    ('z', 'Z (along)', 1),
    ('diameter_cm', 'Diameter (cm)', 0),
    ('clearance_cm', 'Height (cm)', 0),
    ('yaw', 'Heading (deg)', 0),
]
PERSON_FIELDS = [
    ('x', 'X (side)', 1),
    ('y', 'Y (height)', 1),
    ('z', 'Z (along)', 1),
    ('yaw', 'Heading (deg)', 0),
]


class SliderGroup(ttk.Frame):
    """One tab: a picker for which item to edit, plus a slider per field."""

    def __init__(self, parent, fields, on_edit):
        super().__init__(parent, padding=10)
        self._fields = fields
        self._on_edit = on_edit
        self._items = []
        # Set while loading a selection into the sliders. Tkinter's Scale fires
        # its command on a programmatic .set() too, which would echo the value
        # straight back to the simulator as a fresh edit.
        self._suppress = False

        self.selection = tk.StringVar()
        picker = ttk.Combobox(self, textvariable=self.selection, state='readonly')
        picker.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        picker.bind('<<ComboboxSelected>>', lambda _e: self._load_selected())
        self.picker = picker

        self._scales = {}
        self._labels = {}
        for row, (field, label, decimals) in enumerate(fields, start=1):
            text = ttk.Label(self, text=f"{label}: -", width=18)
            text.grid(row=row, column=0, sticky='w')
            scale = ttk.Scale(
                self, orient='horizontal', length=260,
                command=lambda value, f=field: self._on_scale(f, value))
            scale.grid(row=row, column=1, sticky='ew', pady=2)
            self._scales[field] = scale
            self._labels[field] = (text, label, decimals)
        self.columnconfigure(1, weight=1)
        self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        state = 'normal' if enabled else 'disabled'
        self.picker.configure(state='readonly' if enabled else 'disabled')
        for scale in self._scales.values():
            scale.configure(state=state)

    def load(self, items, ranges, names) -> None:
        """Populate from a scene snapshot. `names` labels each item in the picker."""
        self._items = items
        for field, _label, _decimals in self._fields:
            low, high = ranges[field]
            self._scales[field].configure(from_=low, to=high)
        self.picker.configure(values=names)
        # Enable before loading: a disabled ttk.Scale silently ignores set(),
        # so the sliders would come up at zero instead of the scene's values.
        self._set_enabled(bool(names))
        if names:
            keep = self.selection.get()
            self.selection.set(keep if keep in names else names[0])
            self._load_selected()

    @property
    def selected_index(self) -> int:
        values = list(self.picker.cget('values'))
        try:
            return values.index(self.selection.get())
        except ValueError:
            return -1

    def _load_selected(self) -> None:
        index = self.selected_index
        if index < 0:
            return
        item = self._items[index]
        self._suppress = True
        try:
            for field, _label, _decimals in self._fields:
                self._scales[field].set(float(item.get(field, 0)))
                self._refresh_label(field)
        finally:
            self._suppress = False

    def _refresh_label(self, field: str) -> None:
        widget, label, decimals = self._labels[field]
        widget.configure(text=f"{label}: {self._scales[field].get():.{decimals}f}")

    def _on_scale(self, field: str, _value: str) -> None:
        self._refresh_label(field)
        if self._suppress:
            return
        index = self.selected_index
        if index < 0:
            return
        value = round(self._scales[field].get(), 2)
        # Keep the local copy in step so re-selecting doesn't snap back to the
        # value the last snapshot had.
        self._items[index][field] = value
        self._on_edit(self._items[index], field, value)


class SceneEditor:
    def __init__(self, root: tk.Tk, client: SimulatorClient):
        self.root = root
        self.client = client
        self.connected = False
        self._dirty = {}          # (kind, target, field) -> value

        root.title('Tello Sim - Scene Editor')
        root.minsize(420, 300)

        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True)
        self.gates_tab = SliderGroup(notebook, GATE_FIELDS, self._on_gate_edit)
        self.people_tab = SliderGroup(notebook, PERSON_FIELDS, self._on_person_edit)
        notebook.add(self.gates_tab, text='Gates')
        notebook.add(self.people_tab, text='People')

        footer = ttk.Frame(root, padding=(10, 0, 10, 10))
        footer.pack(fill='x')
        self.save_button = ttk.Button(footer, text='Save', command=self._save)
        self.save_button.pack(side='right')
        self.status = tk.StringVar(value='Connecting...')
        ttk.Label(footer, textvariable=self.status).pack(side='left')

        self.root.after(0, self._poll_connection)
        self.root.after(FLUSH_INTERVAL_MS, self._flush)

    # --- connection ----------------------------------------------------------
    def _poll_connection(self) -> None:
        """Wait for the simulator, then load the scene. Also recovers if it restarts."""
        try:
            if not self.connected:
                if self.client.is_simulator_running() and self._load_scene():
                    self.connected = True
                else:
                    self.status.set(
                        f'Waiting for the simulator on {self.client.host}:{self.client.port}...')
                    self.save_button.state(['disabled'])
        except (OSError, KeyError, TypeError, ValueError) as e:
            # A simulator that dies mid-request raises straight through
            # SimConnection (it only catches ConnectionRefusedError), and a
            # truncated snapshot fails the lookups in _load_scene. Either way
            # this is transient — report it and let the next tick retry.
            self.connected = False
            self.status.set(f'Reconnecting after: {e}')
        finally:
            # Always reschedule. Tkinter drops a callback that raises, so a
            # single bad poll would otherwise leave a live window that never
            # reconnects again.
            self.root.after(RECONNECT_INTERVAL_MS, self._poll_connection)

    def _load_scene(self) -> bool:
        scene = self.client.get_scene()
        if not scene or 'ranges' not in scene:
            return False
        ranges = scene['ranges']
        gates = scene.get('gates', [])
        people = scene.get('people', [])
        self.gates_tab.load(
            gates, ranges['gate'],
            [f"Gate {i + 1}: {g.get('color', '?')}" for i, g in enumerate(gates)])
        self.people_tab.load(
            people, ranges['person'],
            [p['name'].replace('_', ' ').title() for p in people])
        self.save_button.state(['!disabled'])
        self.status.set('Connected.')
        return True

    def _disconnected(self) -> None:
        self.connected = False
        self.status.set('Lost the simulator - waiting for it to come back...')

    # --- edits ---------------------------------------------------------------
    def _on_gate_edit(self, gate, field, value) -> None:
        self._dirty[('gate', self.gates_tab.selected_index, field)] = value

    def _on_person_edit(self, person, field, value) -> None:
        self._dirty[('person', person['name'], field)] = value

    def _flush(self) -> None:
        """Send the pending edits, at most one batch per FLUSH_INTERVAL_MS."""
        try:
            if self._dirty and self.connected:
                pending, self._dirty = self._dirty, {}
                items = list(pending.items())
                for position, ((kind, target, field), value) in enumerate(items):
                    try:
                        if kind == 'gate':
                            reply = self.client.set_gate(target, field, value)
                        else:
                            reply = self.client.set_person(target, field, value)
                    except OSError as e:
                        self._requeue(items[position:])
                        self._disconnected()
                        self.status.set(f'Lost the simulator: {e}')
                        break
                    if reply == 'N/A':
                        # SimConnection's "unreachable" sentinel.
                        self._requeue(items[position:])
                        self._disconnected()
                        break
                    if reply.startswith('error'):
                        self._requeue(items[position:])
                        self.status.set(reply)
                        break
                else:
                    self.status.set('Connected.')
        finally:
            # As in _poll_connection: reschedule unconditionally, or one bad
            # batch stops the editor sending anything ever again.
            self.root.after(FLUSH_INTERVAL_MS, self._flush)

    def _requeue(self, unsent) -> None:
        """Put edits that were never sent back on the queue.

        Without this, releasing a slider during a transient error leaves the
        simulator holding an intermediate value while the slider shows the
        final one. setdefault so a newer edit for the same key still wins.
        """
        for key, value in unsent:
            self._dirty.setdefault(key, value)

    def _save(self) -> None:
        reply = self.client.save_scene()
        if reply == 'ok':
            self.status.set('Saved to gates.json and people.json.')
        elif reply == 'N/A':
            self._disconnected()
        else:
            self.status.set(reply)


def main() -> None:
    root = tk.Tk()
    SceneEditor(root, SimulatorClient())
    root.mainloop()


if __name__ == '__main__':
    main()
