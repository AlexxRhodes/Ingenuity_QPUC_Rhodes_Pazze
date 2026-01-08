#!/usr/bin/env python3
# coding: utf-8

import getopt
import atexit
from pathlib import Path
import subprocess
import signal
import sys
import time
import traceback
from typing import List

import ingescape as igs

from gamemaster import QPUCGameMaster


port = 4646
agent_name = "QPUC_GameMaster"
device = None
verbose = False
is_interrupted = False
spawn_controllers = True
spawn_only_controller_j1 = False
controller_processes: List[subprocess.Popen] = []

ready_p1 = False
ready_p2 = False
reset_p1 = False
reset_p2 = False

short_flag = "hvp:d:n:"
long_flag = ["help", "verbose", "port=", "device=", "name=", "no-controllers", "only-controller-j1"]


def print_usage():
    print("Usage:")
    print(f"  {agent_name} --verbose --port 4646 --device <device_name> --name {agent_name}")
    print("  --no-controllers : ne lance pas automatiquement les 2 controllers")
    print("  --only-controller-j1 : lance uniquement le controller du J1 (player 1)")


def _controllers_script_path() -> Path:
    # qpuc_gamemaster_py/main.py -> ../qpuc_controller_py/main.py
    here = Path(__file__).resolve().parent
    return (here.parent / "qpuc_controller_py" / "main.py").resolve()


def _spawn_controllers() -> None:
    global controller_processes

    script = _controllers_script_path()
    if not script.exists():
        print(f"[WARN] Controllers script not found: {script}")
        return

    common = [
        sys.executable,
        str(script),
        "--port",
        str(port),
        "--device",
        str(device),
    ]
    if verbose:
        common.append("--verbose")

    # Lancement local uniquement (même PC que le GameMaster).
    players = ["1"] if spawn_only_controller_j1 else ["1", "2"]
    controller_processes = [subprocess.Popen(common + ["--player", p]) for p in players]


def _stop_controllers() -> None:
    global controller_processes
    for p in controller_processes:
        try:
            if p.poll() is None:
                p.terminate()
        except Exception:
            pass
    controller_processes = []


def signal_handler(signal_received, frame):
    del frame
    global is_interrupted
    print("\n", signal.strsignal(signal_received), sep="")
    is_interrupted = True
    _stop_controllers()


def on_agent_event_callback(event, uuid, name, event_data, my_data):
    del event_data
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        gm.on_agent_event(event, uuid, name)
    except Exception:
        print(traceback.format_exc())


def start_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type, value
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        gm.start_game()
    except Exception:
        print(traceback.format_exc())


def _maybe_autostart_from_ready(gm: QPUCGameMaster) -> None:
    if ready_p1 and ready_p2 and gm.state != "playing":
        gm.start_game()


def reset_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type, value
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        global ready_p1, ready_p2, reset_p1, reset_p2
        ready_p1 = False
        ready_p2 = False
        reset_p1 = False
        reset_p2 = False
        gm.reset()
    except Exception:
        print(traceback.format_exc())


def _maybe_autoreset_from_reset(gm: QPUCGameMaster) -> None:
    global reset_p1, reset_p2
    if reset_p1 and reset_p2:
        reset_p1 = False
        reset_p2 = False
        gm.reset()


def reset_p1_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        global reset_p1
        reset_p1 = bool(value)
        _maybe_autoreset_from_reset(gm)
    except Exception:
        print(traceback.format_exc())


def reset_p2_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        global reset_p2
        reset_p2 = bool(value)
        _maybe_autoreset_from_reset(gm)
    except Exception:
        print(traceback.format_exc())


def ready_p1_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        global ready_p1
        ready_p1 = bool(value)
        _maybe_autostart_from_ready(gm)
    except Exception:
        print(traceback.format_exc())


def ready_p2_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        global ready_p2
        ready_p2 = bool(value)
        _maybe_autostart_from_ready(gm)
    except Exception:
        print(traceback.format_exc())


def click_p1_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.on_click(1, value)
    except Exception:
        print(traceback.format_exc())


def click_p2_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.on_click(2, value)
    except Exception:
        print(traceback.format_exc())


def wb_p1_window_width_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.update_dimensions(player=1, window_width=int(value))
    except Exception:
        print(traceback.format_exc())


def wb_p1_window_height_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.update_dimensions(player=1, window_height=int(value))
    except Exception:
        print(traceback.format_exc())


def wb_p1_whiteboard_width_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.update_dimensions(player=1, whiteboard_width=int(value))
    except Exception:
        print(traceback.format_exc())


def wb_p1_whiteboard_height_input_callback(io_type, name, value_type, value, my_data):
    del io_type, name, value_type
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        if value is not None:
            gm.update_dimensions(player=1, whiteboard_height=int(value))
    except Exception:
        print(traceback.format_exc())




def element_created_service_callback(sender_agent_name, sender_agent_uuid, service_name, tuple_args, token, my_data):
    del sender_agent_name, service_name
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        element_id = int(tuple_args[0])
        gm.on_element_created(sender_agent_uuid, element_id, token)
    except Exception:
        print(traceback.format_exc())


def action_result_service_callback(sender_agent_name, sender_agent_uuid, service_name, tuple_args, token, my_data):
    del sender_agent_name, sender_agent_uuid, service_name, token
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        succeeded = bool(tuple_args[0])
        gm.on_action_result(succeeded)
    except Exception:
        print(traceback.format_exc())


def get_whiteboard_size_result_callback(sender_agent_name, sender_agent_uuid, service_name, tuple_args, token, my_data):
    del sender_agent_name, service_name, token
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        width = int(tuple_args[0])
        height = int(tuple_args[1])
        gm.on_whiteboard_size(sender_agent_uuid, width, height)
    except Exception:
        print(traceback.format_exc())


def timer_timeout(timer_id, my_data):
    del timer_id
    try:
        gm = my_data
        assert isinstance(gm, QPUCGameMaster)
        gm.tick()
        gm.publish_status()
    except Exception:
        print(traceback.format_exc())


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(_stop_controllers)

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_flag, long_flag)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            print_usage()
            sys.exit(0)
        elif o in ("-v", "--verbose"):
            verbose = True
        elif o in ("-p", "--port"):
            port = int(a)
        elif o in ("-d", "--device"):
            device = a
        elif o in ("-n", "--name"):
            agent_name = a
        elif o == "--no-controllers":
            spawn_controllers = False
        elif o == "--only-controller-j1":
            spawn_only_controller_j1 = True
        else:
            raise AssertionError("unhandled option")

    igs.agent_set_name(agent_name)
    igs.definition_set_class("QPUC_GameMaster")
    igs.log_set_console(verbose)
    igs.log_set_file(True, None)
    igs.log_set_stream(verbose)
    igs.set_command_line(sys.executable + " " + " ".join(sys.argv))

    if device is None:
        list_devices = igs.net_devices_list()
        list_addresses = igs.net_addresses_list()
        if len(list_devices) == 1:
            device = list_devices[0]
        elif len(list_devices) == 2 and (list_addresses[0] == "127.0.0.1" or list_addresses[1] == "127.0.0.1"):
            device = list_devices[1] if list_addresses[0] == "127.0.0.1" else list_devices[0]
        else:
            print("Plusieurs interfaces réseau disponibles. Choisis avec --device parmi:")
            for d in list_devices:
                print("  ", d)
            print_usage()
            sys.exit(1)

    if spawn_controllers:
        _spawn_controllers()

    gm = QPUCGameMaster()

    igs.observe_agent_events(on_agent_event_callback, gm)

    # Inputs (à relier depuis Circle)
    igs.input_create("start", igs.IMPULSION_T, None)
    igs.observe_input("start", start_input_callback, gm)

    igs.input_create("reset", igs.IMPULSION_T, None)
    igs.observe_input("reset", reset_input_callback, gm)

    igs.input_create("ready_p1", igs.BOOL_T, None)
    igs.observe_input("ready_p1", ready_p1_input_callback, gm)

    igs.input_create("ready_p2", igs.BOOL_T, None)
    igs.observe_input("ready_p2", ready_p2_input_callback, gm)

    igs.input_create("reset_p1", igs.BOOL_T, None)
    igs.observe_input("reset_p1", reset_p1_input_callback, gm)

    igs.input_create("reset_p2", igs.BOOL_T, None)
    igs.observe_input("reset_p2", reset_p2_input_callback, gm)

    igs.input_create("click_p1", igs.STRING_T, None)
    igs.observe_input("click_p1", click_p1_input_callback, gm)

    igs.input_create("click_p2", igs.STRING_T, None)
    igs.observe_input("click_p2", click_p2_input_callback, gm)

    # Responsive UI: dimensions venant des Whiteboards (à relier depuis Circle)
    # Whiteboard outputs: windowWidth/windowHeight/whiteboardWidth/whiteboardHeight
    igs.input_create("wb_p1_windowWidth", igs.INTEGER_T, None)
    igs.observe_input("wb_p1_windowWidth", wb_p1_window_width_input_callback, gm)
    igs.input_create("wb_p1_windowHeight", igs.INTEGER_T, None)
    igs.observe_input("wb_p1_windowHeight", wb_p1_window_height_input_callback, gm)
    igs.input_create("wb_p1_whiteboardWidth", igs.INTEGER_T, None)
    igs.observe_input("wb_p1_whiteboardWidth", wb_p1_whiteboard_width_input_callback, gm)
    igs.input_create("wb_p1_whiteboardHeight", igs.INTEGER_T, None)
    igs.observe_input("wb_p1_whiteboardHeight", wb_p1_whiteboard_height_input_callback, gm)

    # Pas de Whiteboard pour J2: seulement P1 (GameMaster)

    # Outputs (debug / supervision)
    igs.output_create("state", igs.STRING_T, None)
    igs.output_create("turn", igs.INTEGER_T, None)
    igs.output_create("time_left", igs.INTEGER_T, None)
    igs.output_create("score_p1", igs.INTEGER_T, None)
    igs.output_create("score_p2", igs.INTEGER_T, None)

    # Services (Whiteboard -> GameMaster)
    igs.service_init("elementCreated", element_created_service_callback, gm)
    igs.service_arg_add("elementCreated", "elementId", igs.INTEGER_T)

    igs.service_init("actionResult", action_result_service_callback, gm)
    igs.service_arg_add("actionResult", "succeeded", igs.BOOL_T)

    igs.service_init("getWhiteboardSizeResult", get_whiteboard_size_result_callback, gm)
    igs.service_arg_add("getWhiteboardSizeResult", "width", igs.INTEGER_T)
    igs.service_arg_add("getWhiteboardSizeResult", "height", igs.INTEGER_T)

    igs.start_with_device(device, port)

    timer_id = igs.timer_start(200, 0, timer_timeout, gm)

    gm.reset()

    while (not is_interrupted) and igs.is_started():
        time.sleep(0.1)

    igs.timer_stop(timer_id)
    _stop_controllers()
