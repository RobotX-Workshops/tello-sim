"""
This module initializes a connection to a Tello drone and sets up a control interface
using a game controller or keyboard input. The script can auto-detect the controller 
when the 'auto' mode is specified or use a specific controller type provided as an 
argument. It continuously polls the controller's state and dispatches commands to the drone 
at a configurable cadence. Logging is configured via command-line arguments to facilitate 
debugging and monitoring.
"""

import sys
import os
import time
import argparse
import logging
from typing import Dict, Callable, Literal

# Ensure parent directory is in sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.join(script_dir, "..")
sys.path.append(parent_dir)

from djitellopy import Tello

from services.tello_command_dispatcher import TelloCommandDispatcher
from services.tello_connector import TelloConnector
from joysticks.pygame_connector import PyGameConnector
from joysticks.game_controller_type import GameControllerType
from joysticks.xbox_one_controller import XboxOnePyGameController
from joysticks.xbox_controller import XboxPyGameController
from services.tello_controller import TelloController
from controller_adapters.keyboard_controller import KeyboardControlAdapter
from controller_adapters.xbox_one_tello_adapter import XboxOneTelloControlAdapter
from controller_adapters.xbox_controller_tello_adapter import XboxTelloControlAdapter

LOGGER = logging.getLogger(__name__)

# Mapping from GameControllerType to its adapter factory
_CONTROLLER_ID_CLASS_MAPPING: Dict[
    GameControllerType, Callable[[PyGameConnector], TelloController]
] = {
    GameControllerType.XBOX360: lambda connector: XboxTelloControlAdapter(
        XboxPyGameController(connector)
    ),
    GameControllerType.KEYBOARD: lambda connector: KeyboardControlAdapter(connector),
    GameControllerType.XBOXONE: lambda connector: XboxOneTelloControlAdapter(
        XboxOnePyGameController(connector)
    ),
}

def get_controller_type(platform: str, joystick_name: str) -> GameControllerType:
    # Adjust these mappings as needed for your environment
    mapping = {
        "linux": {},
        "darwin": {"Xbox Series X Controller": GameControllerType.XBOX360},
        "win32": {},
    }
    try:
        return mapping[platform][joystick_name]
    except KeyError:
        raise ValueError(
            f"No controller mapping found for platform {platform} and joystick '{joystick_name}'"
        )


def get_tello_control(controller_arg: str) -> TelloController:
    """
    Get the TelloController instance based on the controller_arg.
    If controller_arg is 'auto', the controller will be auto-detected.
    """
    pygame_connector = PyGameConnector()
    if controller_arg.lower() != "auto":
        try:
            controller_type = GameControllerType[controller_arg.upper()]
            tello_controller_adapter = _CONTROLLER_ID_CLASS_MAPPING[controller_type](pygame_connector)
        except KeyError:
            raise ValueError(f"Unsupported controller type for auto detection: {controller_arg}")
    elif controller_arg.lower() == "keyboard":
        tello_controller_adapter = KeyboardControlAdapter(pygame_connector)
    else:
        # Auto-detect controller via joystick initialization
        try:
            pygame_connector.init_joystick()
            joystick = pygame_connector.create_joystick(0)
            joystick.init()
            joystick_name = joystick.get_name()
            platform_str = sys.platform
            controller_type = get_controller_type(platform_str, joystick_name)
            tello_controller_adapter = _CONTROLLER_ID_CLASS_MAPPING[controller_type](pygame_connector)
        except (KeyError, ValueError) as e:
            LOGGER.error("Error detecting controller: %s", e)
            LOGGER.info("Defaulting to Keyboard Controller")
            tello_controller_adapter = KeyboardControlAdapter(pygame_connector)
    return tello_controller_adapter


def get_command_dispatcher() -> TelloCommandDispatcher:
    """
    Creates and connects to the Tello drone and returns a instance used for dispatching commands to the tello.
    """
    tello = Tello()
    tello_connector = TelloConnector(tello)
    tello_connector.connect()
    command_dispatcher = TelloCommandDispatcher(tello_connector)
    return command_dispatcher

def main(
    controller_arg: Literal["xbox360", "keyboard", "xboxone", "auto"],
    cadence_secs: float,
    log_level: str,
) -> None:
    logging.basicConfig(level=log_level)

    # Connecto to the controller
    tello_controller = get_tello_control(controller_arg)
    # Connect to the Tello drone
    command_dispatcher = get_command_dispatcher()
    
    # Main loop: get control state and dispatch commands at the specified cadence
    while True:
        time.sleep(cadence_secs)
        try:
            control_state = tello_controller.get_state()
            command_dispatcher.send_commands(control_state)
        except Exception as e:
            LOGGER.error("Error issuing command: %s", e)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--controller",
        default="auto",
        choices=["xbox360", "keyboard", "xboxone", "auto"],
        help="Specify the controller type, or 'auto' to detect (default: auto)",
    )
    parser.add_argument(
        "--cadence",
        type=float,
        default=0.1,
        help="Specify the loop cadence in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Specify the logging level (default: INFO)",
    )
    args = parser.parse_args()
    main(args.controller, args.cadence, args.log_level)
