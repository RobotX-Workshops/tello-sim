"""Start the simulator and the scene editor together.

Panda3D has to own the main thread, so this does not import the simulator — it
spawns both as child processes and supervises them. Closing the simulator (or
Ctrl-C here) shuts the editor down too, so neither is left orphaned.

    python run.py                 # both windows
    python run.py --no-editor     # simulator only
    python run.py --editor-only   # attach to a simulator that's already running
"""
import argparse
import os
import signal
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(REPO_ROOT, 'tello_sim', 'run_sim.py')
EDITOR = os.path.join(REPO_ROOT, 'tools', 'scene_editor.py')


def _spawn(script: str) -> subprocess.Popen:
    """Run one script with this interpreter and the repo root importable."""
    # Prepend rather than replace: whatever the caller already had on
    # PYTHONPATH is theirs, and clobbering it can break their environment.
    existing = os.environ.get('PYTHONPATH')
    path = f"{REPO_ROOT}{os.pathsep}{existing}" if existing else REPO_ROOT
    env = dict(os.environ, PYTHONPATH=path)
    return subprocess.Popen([sys.executable, script], env=env, cwd=REPO_ROOT)


def _has_tk() -> bool:
    """Whether this interpreter can open a Tk window.

    Homebrew's Python ships without Tk unless python-tk is installed, so the
    editor would otherwise start and immediately die with an ImportError
    buried in the simulator's output.
    """
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


def _warn_no_tk(then: str) -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"[run] {sys.executable} has no tkinter, so the scene editor cannot start.")
    print(f"[run] On macOS with Homebrew Python: brew install python-tk@{version}")
    print(f"[run] {then}")


def _shutdown(process: subprocess.Popen) -> None:
    """Ask a child to exit, then insist if it doesn't."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _exit_on_signal(signum, _frame):
    raise SystemExit(128 + signum)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--no-editor', action='store_true',
                       help="start the simulator on its own")
    group.add_argument('--editor-only', action='store_true',
                       help="start the scene editor and attach to a running simulator")
    args = parser.parse_args()

    if args.editor_only:
        if not _has_tk():
            _warn_no_tk("Nothing to run.")
            return 1
        return _spawn(EDITOR).wait()

    want_editor = not args.no_editor
    if want_editor and not _has_tk():
        _warn_no_tk("Starting the simulator on its own.")
        want_editor = False

    # `kill` on this process would otherwise orphan both windows, since the
    # children are only signalled when Ctrl-C hits the whole process group.
    # Turn SIGTERM into a normal exit so the cleanup below always runs.
    signal.signal(signal.SIGTERM, _exit_on_signal)

    # The editor starts first because it polls until the simulator answers, so
    # it can come up while the 3D window is still loading its models.
    editor = _spawn(EDITOR) if want_editor else None
    sim = _spawn(SIM)
    try:
        return sim.wait()
    except (KeyboardInterrupt, SystemExit):
        # Ctrl-C already reached the whole process group, so the children are
        # usually winding down anyway; shut them down explicitly regardless.
        return 130
    finally:
        # Both children, on every exit path — a half-torn-down pair leaves a
        # window with no simulator behind it, or a port 9999 nobody can rebind.
        _shutdown(sim)
        if editor is not None:
            _shutdown(editor)


if __name__ == '__main__':
    sys.exit(main())
