#!/usr/bin/env python3
# coding: utf-8

import getopt
import signal
import sys
import traceback

import ingescape as igs


port = 4646
device = None
verbose = False
player = 1
agent_name = None

short_flag = "hvp:d:n:P:"
long_flag = ["help", "verbose", "port=", "device=", "name=", "player="]


_ui_root = None
_ui_ready_btn = None
_ui_reset_btn = None
_ready_sent = False
_reset_sent = False
_gm_state = ""


def _theme_apply_button(btn, *, kind: str, checked: bool, enabled: bool) -> None:
    """Applique un style simple et lisible aux boutons Tkinter."""
    # Palette sobre (fonctionne correctement sous Windows avec tk.Button).
    colors = {
        "ready": {"base": "#2563EB", "active": "#1D4ED8"},
        "reset": {"base": "#F97316", "active": "#EA580C"},
        "choice": {"base": "#111827", "active": "#0B1220"},
    }

    c = colors.get(kind, colors["choice"])
    bg = c["base"]
    active_bg = c["active"]

    # L'état "checked" est rendu via une légère variation pour éviter les ✅ uniquement.
    if checked:
        # teinte un peu plus claire
        bg = active_bg
        active_bg = bg

    if not enabled:
        # gris neutre
        bg = "#374151"
        active_bg = bg

    btn.configure(
        bg=bg,
        fg="#F9FAFB",
        activebackground=active_bg,
        activeforeground="#F9FAFB",
        disabledforeground="#E5E7EB",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2" if enabled else "arrow",
        state="normal" if enabled else "disabled",
    )


def print_usage():
    print("Usage:")
    print("  python main.py --player 1 --port 4646 --device <device> --verbose")
    print("  python main.py --player 2 --port 4646 --device <device> --verbose")


def pick_device_or_exit() -> str:
    global device
    if device is not None:
        return device

    list_devices = igs.net_devices_list()
    list_addresses = igs.net_addresses_list()
    if len(list_devices) == 1:
        device = list_devices[0]
        return device
    if len(list_devices) == 2 and (list_addresses[0] == "127.0.0.1" or list_addresses[1] == "127.0.0.1"):
        device = list_devices[1] if list_addresses[0] == "127.0.0.1" else list_devices[0]
        return device

    print("Plusieurs interfaces réseau disponibles. Choisis avec --device parmi:")
    for d in list_devices:
        print("  ", d)
    print_usage()
    sys.exit(1)


def set_answer(value: str) -> None:
    # Réponse en sortie: à relier vers le GameMaster.
    igs.output_set_string("answer", value)


def set_ready(value: bool = True) -> None:
    igs.output_set_bool("ready", bool(value))


def set_reset(value: bool = True) -> None:
    igs.output_set_bool("reset", bool(value))


def _apply_gm_state(state: str) -> None:
    global _ui_root, _ui_ready_btn, _ui_reset_btn, _ready_sent, _reset_sent, _gm_state
    if _ui_root is None:
        return

    s = (state or "").strip().lower()

    def _do():
        global _ready_sent, _reset_sent, _gm_state
        nonlocal s
        _gm_state = s
        # idle: réarmer les boutons
        if s == "idle" or s == "":
            _ready_sent = False
            _reset_sent = False
            set_ready(False)
            set_reset(False)
            if _ui_ready_btn is not None:
                _ui_ready_btn.configure(text="Prêt")
                _theme_apply_button(_ui_ready_btn, kind="ready", checked=False, enabled=True)
            if _ui_reset_btn is not None:
                _ui_reset_btn.configure(text="Reset")
                _theme_apply_button(_ui_reset_btn, kind="reset", checked=False, enabled=True)
            return

        # playing: décocher + désactiver Prêt ; laisser Reset dispo
        if s == "playing":
            set_ready(False)
            _ready_sent = False
            if _ui_ready_btn is not None:
                _ui_ready_btn.configure(text="Prêt")
                _theme_apply_button(_ui_ready_btn, kind="ready", checked=False, enabled=False)
            if _ui_reset_btn is not None:
                _ui_reset_btn.configure(text=("Reset ✅" if _reset_sent else "Reset"))
                _theme_apply_button(_ui_reset_btn, kind="reset", checked=_reset_sent, enabled=True)
            return

        # game_over: Prêt désactivé, Reset dispo
        if s == "game_over":
            set_ready(False)
            _ready_sent = False
            if _ui_ready_btn is not None:
                _ui_ready_btn.configure(text="Prêt")
                _theme_apply_button(_ui_ready_btn, kind="ready", checked=False, enabled=False)
            if _ui_reset_btn is not None:
                _ui_reset_btn.configure(text=("Reset ✅" if _reset_sent else "Reset"))
                _theme_apply_button(_ui_reset_btn, kind="reset", checked=_reset_sent, enabled=True)
            return

    # Tkinter n'est pas thread-safe: on planifie sur le thread UI.
    _ui_root.after(0, _do)


def build_tk_ui(title: str):
    # UI ultra simple: 4 boutons + hotkeys.
    import tkinter as tk

    root = tk.Tk()
    root.title(title)
    root.geometry("520x500")
    root.resizable(False, False)

    # Fond + panneaux
    root.configure(bg="#0B1220")

    header = tk.Label(
        root,
        text=title,
        font=("Segoe UI", 16, "bold"),
        bg="#0B1220",
        fg="#F9FAFB",
    )
    header.pack(pady=(14, 4))

    info = tk.Label(
        root,
        text="1) Clique sur Prêt  •  2) Répond A/B/C/D",
        font=("Segoe UI", 11),
        bg="#0B1220",
        fg="#9CA3AF",
    )
    info.pack(pady=(0, 12))

    frame = tk.Frame(root, bg="#0B1220")
    frame.pack(pady=8)

    ready_btn = tk.Button(
        frame,
        text="Prêt",
        width=18,
        height=2,
        font=("Segoe UI", 14, "bold"),
    )

    reset_btn = tk.Button(
        frame,
        text="Reset",
        width=18,
        height=2,
        font=("Segoe UI", 14, "bold"),
    )

    # Applique le thème initial
    _theme_apply_button(ready_btn, kind="ready", checked=False, enabled=True)
    _theme_apply_button(reset_btn, kind="reset", checked=False, enabled=True)

    def on_ready():
        global _ready_sent, _gm_state
        # Prêt n'est pertinent qu'à l'état idle (avant le lancement).
        if (_gm_state or "").strip().lower() not in ("", "idle"):
            return
        _ready_sent = not _ready_sent
        set_ready(_ready_sent)
        ready_btn.configure(text=("Prêt ✅" if _ready_sent else "Prêt"))
        _theme_apply_button(ready_btn, kind="ready", checked=_ready_sent, enabled=True)

    def on_reset():
        global _reset_sent
        _reset_sent = not _reset_sent
        set_reset(_reset_sent)
        reset_btn.configure(text=("Reset ✅" if _reset_sent else "Reset"))
        _theme_apply_button(reset_btn, kind="reset", checked=_reset_sent, enabled=True)

    ready_btn.configure(command=on_ready)
    ready_btn.grid(row=0, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

    reset_btn.configure(command=on_reset)
    reset_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

    def make_btn(letter: str):
        btn = tk.Button(
            frame,
            text=letter,
            width=8,
            height=2,
            font=("Segoe UI", 18, "bold"),
            command=lambda: set_answer(letter),
        )
        _theme_apply_button(btn, kind="choice", checked=False, enabled=True)
        return btn

    btn_a = make_btn("A")
    btn_b = make_btn("B")
    btn_c = make_btn("C")
    btn_d = make_btn("D")

    btn_a.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
    btn_b.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
    btn_c.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
    btn_d.grid(row=3, column=1, padx=10, pady=10, sticky="nsew")

    # Rendre la grille plus "propre" visuellement
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    root.bind("a", lambda e: set_answer("A"))
    root.bind("b", lambda e: set_answer("B"))
    root.bind("c", lambda e: set_answer("C"))
    root.bind("d", lambda e: set_answer("D"))
    root.bind("A", lambda e: set_answer("A"))
    root.bind("B", lambda e: set_answer("B"))
    root.bind("C", lambda e: set_answer("C"))
    root.bind("D", lambda e: set_answer("D"))

    root.bind("<Return>", lambda e: on_ready())
    root.bind("<space>", lambda e: on_ready())

    def on_close():
        try:
            igs.stop()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # publish handles for state updates
    global _ui_root, _ui_ready_btn, _ui_reset_btn
    _ui_root = root
    _ui_ready_btn = ready_btn
    _ui_reset_btn = reset_btn
    return root


def main():
    global port, device, verbose, player, agent_name

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_flag, long_flag)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            print_usage()
            return 0
        if o in ("-v", "--verbose"):
            verbose = True
        elif o in ("-p", "--port"):
            port = int(a)
        elif o in ("-d", "--device"):
            device = a
        elif o in ("-n", "--name"):
            agent_name = a
        elif o in ("-P", "--player"):
            player = int(a)
        else:
            raise AssertionError("unhandled option")

    if agent_name is None:
        agent_name = f"QPUC_Controller_P{player}"

    igs.agent_set_name(agent_name)
    igs.definition_set_class("QPUC_Controller")
    igs.log_set_console(verbose)
    igs.log_set_file(True, None)
    igs.log_set_stream(verbose)
    igs.set_command_line(sys.executable + " " + " ".join(sys.argv))

    # outputs
    igs.output_create("answer", igs.STRING_T, None)
    igs.output_create("ready", igs.BOOL_T, None)
    igs.output_set_bool("ready", False)
    igs.output_create("reset", igs.BOOL_T, None)
    igs.output_set_bool("reset", False)

    # input from GameMaster for UI sync
    def gm_state_input_callback(io_type, name, value_type, value, my_data):
        del io_type, name, value_type, my_data
        try:
            _apply_gm_state(str(value) if value is not None else "")
        except Exception:
            print(traceback.format_exc())

    igs.input_create("gm_state", igs.STRING_T, None)
    igs.observe_input("gm_state", gm_state_input_callback, None)

    dev = pick_device_or_exit()
    igs.start_with_device(dev, port)

    # GUI
    title = f"QPUC Controller - Joueur {player}"
    try:
        root = build_tk_ui(title)
    except Exception as e:
        igs.error(f"Tkinter indisponible: {e}")
        print("Tkinter indisponible; utilise une autre UI ou installe Python complet.")
        return 1

    root.mainloop()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        print(traceback.format_exc())
        raise
