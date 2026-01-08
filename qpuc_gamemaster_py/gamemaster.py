from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Dict, List, Optional, Tuple

import ingescape as igs

from trivia import OpenTDBClient, TriviaQuestion


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= (self.x + self.w) and self.y <= py <= (self.y + self.h)


class QPUCGameMaster:
    TURN_SECONDS = 45
    TARGET_SCORE = 4

    # UI theme (simple, high-contrast, compatible with Whiteboard primitives)
    UI_BG = "#0B1220"
    UI_PANEL = "#111827"
    UI_CARD = "#F9FAFB"
    UI_CARD_BORDER = "#CBD5E1"
    UI_TEXT_LIGHT = "#F9FAFB"
    UI_TEXT_MUTED = "#94A3B8"
    UI_ACCENT = "#2563EB"

    def _wrap_text(self, text: str, *, max_chars: int, max_lines: int) -> str:
        """Wrap simple (sans mesures de police) pour addText.

        Whiteboard n'ayant pas forcément de wrap natif, on insère des '\n'.
        """
        if not text:
            return ""

        max_chars = max(10, int(max_chars))
        max_lines = max(1, int(max_lines))

        # Respecte les retours déjà présents
        raw_lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out_lines: List[str] = []

        def push_line(line: str) -> None:
            nonlocal out_lines
            if len(out_lines) < max_lines:
                out_lines.append(line)

        for raw in raw_lines:
            words = raw.split()
            if not words:
                push_line("")
                continue

            current = words[0]
            for w in words[1:]:
                if len(current) + 1 + len(w) <= max_chars:
                    current = f"{current} {w}"
                else:
                    push_line(current)
                    current = w
                    if len(out_lines) >= max_lines:
                        break

            if len(out_lines) >= max_lines:
                break
            push_line(current)
            if len(out_lines) >= max_lines:
                break

        # Ellipsis si on a tronqué
        if len(out_lines) >= max_lines:
            last = out_lines[max_lines - 1]
            if not last.endswith("…"):
                if len(last) >= 1:
                    out_lines[max_lines - 1] = (last[: max(0, max_chars - 1)].rstrip() + "…")
                else:
                    out_lines[max_lines - 1] = "…"

        return "\n".join(out_lines)

    def _estimate_chars_per_line(self, pixel_width: float) -> int:
        """Heuristique: ~9-10px/char (Segoe UI par défaut)."""
        # On évite les valeurs trop petites sur petites résolutions.
        return max(18, int(pixel_width / 10.0))

    def __init__(self):
        self._trivia = OpenTDBClient()
        self._buffer: List[TriviaQuestion] = []

        self.p1_name = "J1"
        self.p2_name = "J2"

        # Whiteboards (UUIDs)
        self.wb_p1_uuid: Optional[str] = None

        # Latest sizes (per Whiteboard uuid)
        self._wb_size: Dict[str, Tuple[int, int]] = {}  # fallback via getWhiteboardSize
        self._wb_window_size: Dict[str, Tuple[int, int]] = {}
        self._wb_area_size: Dict[str, Tuple[int, int]] = {}  # from whiteboardWidth/Height outputs
        # Un seul Whiteboard (celui du GameMaster). J2 n'a pas de Whiteboard.
        self._player_dims: Dict[int, Dict[str, int]] = {1: {}}

        # element ids (per Whiteboard uuid)
        self._timer_text_id: Dict[str, int] = {}
        self._score_text_id: Dict[str, int] = {}
        self._turn_text_id: Dict[str, int] = {}

        # Game state
        self.state: str = "idle"  # idle | playing | game_over
        self.turn: int = 1  # 1 or 2
        self.score_p1: int = 0
        self.score_p2: int = 0
        self._current_question: Optional[TriviaQuestion] = None
        self._turn_deadline: Optional[float] = None
        self._answered_this_turn: bool = False

        # Layout cached (per whiteboard uuid)
        self._choice_rects_by_wb: Dict[str, List[Rect]] = {}
        self._layout_by_wb: Dict[str, Dict[str, float]] = {}

    # -------------------------
    # Ingescape-facing helpers
    # -------------------------

    def publish_status(self) -> None:
        igs.output_set_string("state", self.state)
        igs.output_set_int("turn", self.turn)
        igs.output_set_int("score_p1", self.score_p1)
        igs.output_set_int("score_p2", self.score_p2)
        igs.output_set_int("time_left", self.time_left_s())

    def time_left_s(self) -> int:
        if self.state != "playing" or self._turn_deadline is None:
            return 0
        return max(0, int(self._turn_deadline - time.monotonic()))

    def _wb_call(self, wb_uuid: str, service: str, args, token: Optional[str] = None) -> None:
        try:
            igs.service_call(wb_uuid, service, args, token)
        except Exception as e:
            igs.error(f"service_call failed: wb={wb_uuid} service={service}: {e}")

    def _all_whiteboards(self) -> List[str]:
        out: List[str] = []
        if self.wb_p1_uuid:
            out.append(self.wb_p1_uuid)
        return out

    # -------------------------
    # Whiteboard discovery
    # -------------------------

    def on_agent_event(self, event: int, uuid: str, name: str) -> None:
        if name != "Whiteboard":
            return

        if event == igs.AGENT_KNOWS_US:
            self._register_whiteboard(uuid)
        elif event == igs.AGENT_EXITED:
            self._unregister_whiteboard(uuid)

    def _register_whiteboard(self, wb_uuid: str) -> None:
        if self.wb_p1_uuid is None:
            self.wb_p1_uuid = wb_uuid
            igs.info(f"Whiteboard affectée à P1 (uuid={wb_uuid})")
        else:
            igs.warn(f"Whiteboard supplémentaire ignorée (uuid={wb_uuid})")
            return

        # Init UI
        self._wb_call(wb_uuid, "clear", None, None)
        self._wb_call(wb_uuid, "hideLabels", None, None)
        self._wb_call(wb_uuid, "setTitle", ("QPUC - 4 à la suite",), None)
        self._wb_call(wb_uuid, "getWhiteboardSize", None, f"{wb_uuid}:size")

        # Si Circle envoie déjà les dimensions via outputs, les appliquer maintenant
        self._apply_player_dims_to_uuid()
        self._compute_layout_for_wb(wb_uuid)

        # Si on a déjà démarré, redraw
        self.render_all()

    def _unregister_whiteboard(self, wb_uuid: str) -> None:
        if self.wb_p1_uuid == wb_uuid:
            self.wb_p1_uuid = None
        self._wb_size.pop(wb_uuid, None)
        self._wb_window_size.pop(wb_uuid, None)
        self._wb_area_size.pop(wb_uuid, None)
        self._timer_text_id.pop(wb_uuid, None)
        self._score_text_id.pop(wb_uuid, None)
        self._turn_text_id.pop(wb_uuid, None)
        self._choice_rects_by_wb.pop(wb_uuid, None)
        self._layout_by_wb.pop(wb_uuid, None)
        igs.warn(f"Whiteboard sortie (uuid={wb_uuid})")

    def update_dimensions(
        self,
        *,
        player: int,
        window_width: Optional[int] = None,
        window_height: Optional[int] = None,
        whiteboard_width: Optional[int] = None,
        whiteboard_height: Optional[int] = None,
    ) -> None:
        """Reçoit les dimensions depuis les outputs des Whiteboards (via liens Circle)."""
        if player != 1:
            return

        d = self._player_dims[player]
        if window_width is not None:
            d["windowWidth"] = int(window_width)
        if window_height is not None:
            d["windowHeight"] = int(window_height)
        if whiteboard_width is not None:
            d["whiteboardWidth"] = int(whiteboard_width)
        if whiteboard_height is not None:
            d["whiteboardHeight"] = int(whiteboard_height)

        self._apply_player_dims_to_uuid()
        for wb_uuid in self._all_whiteboards():
            self._compute_layout_for_wb(wb_uuid)
        self.render_all(clear_first=True)

    def _apply_player_dims_to_uuid(self) -> None:
        # Map dims for player 1
        if self.wb_p1_uuid:
            d1 = self._player_dims.get(1, {})
            if "windowWidth" in d1 and "windowHeight" in d1:
                self._wb_window_size[self.wb_p1_uuid] = (int(d1["windowWidth"]), int(d1["windowHeight"]))
            if "whiteboardWidth" in d1 and "whiteboardHeight" in d1:
                self._wb_area_size[self.wb_p1_uuid] = (int(d1["whiteboardWidth"]), int(d1["whiteboardHeight"]))

    def _get_whiteboard_area_size(self, wb_uuid: str) -> Tuple[int, int]:
        if wb_uuid in self._wb_area_size:
            return self._wb_area_size[wb_uuid]
        if wb_uuid in self._wb_size:
            return self._wb_size[wb_uuid]
        return (680, 443)

    # -------------------------
    # Game flow
    # -------------------------

    def start_game(self) -> None:
        self.state = "playing"
        self.turn = 1
        self.score_p1 = 0
        self.score_p2 = 0
        self._answered_this_turn = False
        self._turn_deadline = time.monotonic() + self.TURN_SECONDS
        self._ensure_question()
        for wb_uuid in self._all_whiteboards():
            self._compute_layout_for_wb(wb_uuid)
        self.render_all(clear_first=True)
        self.publish_status()

    def reset(self) -> None:
        self.state = "idle"
        self._current_question = None
        self._turn_deadline = None
        self._answered_this_turn = False
        self.publish_status()
        self.render_all(clear_first=True)

    def _ensure_question(self) -> None:
        if self._buffer:
            self._current_question = self._buffer.pop(0)
            return
        try:
            self._buffer = self._trivia.fetch_many(amount=10)
        except Exception as e:
            igs.error(f"Impossible de récupérer des questions (API): {e}")
            self._buffer = []
        self._current_question = self._buffer.pop(0) if self._buffer else None

    def _next_turn(self) -> None:
        if self.score_p1 >= self.TARGET_SCORE or self.score_p2 >= self.TARGET_SCORE:
            self.state = "game_over"
            self._turn_deadline = None
            self.publish_status()
            self.render_all(clear_first=True)
            return

        self.turn = 2 if self.turn == 1 else 1
        self._answered_this_turn = False
        self._turn_deadline = time.monotonic() + self.TURN_SECONDS
        self._ensure_question()
        for wb_uuid in self._all_whiteboards():
            self._compute_layout_for_wb(wb_uuid)
        self.render_all(clear_first=True)
        self.publish_status()

    def tick(self) -> None:
        if self.state != "playing":
            return

        left = self.time_left_s()
        self._update_timer_texts(left)
        if self._turn_deadline is not None and time.monotonic() >= self._turn_deadline:
            # Temps écoulé -> 0 point, passe au joueur suivant
            self._next_turn()

    # -------------------------
    # Click handling
    # -------------------------

    def on_click(self, player: int, click_json: str) -> None:
        if self.state != "playing":
            return
        if player != self.turn:
            return
        if self._answered_this_turn:
            return
        if not self._current_question:
            return

        # Two possible modes depending on Whiteboard version:
        # 1) click_json is a JSON string {"x":...,"y":...} from output `click`
        # 2) click_json is a chat-like answer (A/B/C/D or 1-4) coming from `lastChatMessage`
        choice_index: Optional[int] = None

        # Mode 1: JSON click
        try:
            obj = json.loads(click_json)
            if isinstance(obj, dict) and ("x" in obj) and ("y" in obj):
                x_raw = obj.get("x")
                y_raw = obj.get("y")
                if x_raw is not None and y_raw is not None:
                    x = float(x_raw)
                    y = float(y_raw)
                    choice_index = self._hit_test_choice(player, x, y)
        except Exception:
            pass

        # Mode 2: text answer
        if choice_index is None:
            choice_index = self._parse_text_answer(click_json)

        if choice_index is None:
            return

        self._answered_this_turn = True

        if choice_index == self._current_question.correct_index:
            if player == 1:
                self.score_p1 += 1
            else:
                self.score_p2 += 1

        # Feedback rapide: on recolore la case cliquée
        self._flash_choice(choice_index, correct=(choice_index == self._current_question.correct_index))

        self.publish_status()
        self._next_turn()

    def _parse_text_answer(self, raw: str) -> Optional[int]:
        if raw is None:
            return None
        s = str(raw).strip().upper()
        # Accept messages like "A", "B", "C", "D" or "1".."4".
        # Some UIs may send "A) ..." or "A." -> keep first char.
        if not s:
            return None

        first = s[0]
        if first in ("A", "B", "C", "D"):
            return ord(first) - ord("A")

        if first in ("1", "2", "3", "4"):
            return int(first) - 1

        return None

    def _hit_test_choice(self, player: int, x: float, y: float) -> Optional[int]:
        # Un seul Whiteboard: on hit-test sur celui-ci, quel que soit le joueur.
        wb_uuid = self.wb_p1_uuid
        if not wb_uuid:
            return None
        rects = self._choice_rects_by_wb.get(wb_uuid)
        if not rects:
            self._compute_layout_for_wb(wb_uuid)
            rects = self._choice_rects_by_wb.get(wb_uuid, [])

        for i, r in enumerate(rects):
            if r.contains(x, y):
                return i
        return None

    # -------------------------
    # Rendering
    # -------------------------

    def _compute_layout_for_wb(self, wb_uuid: str) -> None:
        # Layout responsive en coordonnées WhiteboardArea.
        w_i, h_i = self._get_whiteboard_area_size(wb_uuid)
        w = float(w_i)
        h = float(h_i)

        margin = 20.0
        inner_pad = 10.0
        gap = 14.0

        header_h = 100.0
        # Décalage visuel demandé pour descendre le bloc question
        q_offset_y = 50.0
        q_panel_x = margin
        q_panel_y = header_h + 10.0 + q_offset_y
        q_panel_w = max(260.0, w - 2.0 * margin)
        # On garde un panneau question assez grand pour 2-3 lignes + hint, sans manger tout l'écran.
        q_panel_h = min(150.0, max(105.0, h * 0.28))

        grid_top = q_panel_y + q_panel_h + 16.0
        grid_h = max(120.0, h - grid_top - margin)
        grid_w = max(260.0, w - 2.0 * (margin + inner_pad))

        # On réduit un peu les cartes par défaut pour laisser respirer l'UI.
        max_card_h = 88.0
        max_card_w = (grid_w - gap) / 2.0
        card_h = min(max_card_h, (grid_h - gap) / 2.0)
        card_w = min(max_card_w, (grid_w - gap) / 2.0)

        total_w = 2.0 * card_w + gap
        total_h = 2.0 * card_h + gap

        x0 = (w - total_w) / 2.0
        x0 = max(margin, x0)
        y0 = grid_top + max(0.0, (grid_h - total_h) / 2.0)

        self._choice_rects_by_wb[wb_uuid] = [
            Rect(x0, y0, card_w, card_h),
            Rect(x0 + card_w + gap, y0, card_w, card_h),
            Rect(x0, y0 + card_h + gap, card_w, card_h),
            Rect(x0 + card_w + gap, y0 + card_h + gap, card_w, card_h),
        ]

        # Layout values used by renderer
        self._layout_by_wb[wb_uuid] = {
            "w": w,
            "h": h,
            "margin": margin,
            "header_h": header_h,
            "q_panel_x": q_panel_x,
            "q_panel_y": q_panel_y,
            "q_panel_w": q_panel_w,
            "q_panel_h": q_panel_h,
            "q_text_x": q_panel_x + 12.0,
            "q_text_y": q_panel_y + 14.0,
            "hint_y": q_panel_y + q_panel_h - 53.0,
            "grid_top": grid_top,
        }

    def render_all(self, *, clear_first: bool = False) -> None:
        for wb_uuid in self._all_whiteboards():
            self._render_one(wb_uuid, clear_first=clear_first)

    def _render_one(self, wb_uuid: str, *, clear_first: bool) -> None:
        if clear_first:
            self._wb_call(wb_uuid, "clear", None, None)
            self._wb_call(wb_uuid, "hideLabels", None, None)
            self._timer_text_id.pop(wb_uuid, None)
            self._score_text_id.pop(wb_uuid, None)
            self._turn_text_id.pop(wb_uuid, None)

        # Ensure layout exists for this whiteboard
        if wb_uuid not in self._layout_by_wb:
            self._compute_layout_for_wb(wb_uuid)

        layout = self._layout_by_wb.get(wb_uuid, {})
        rects = self._choice_rects_by_wb.get(wb_uuid, [])

        # Determine target size (for background/panels)
        w = float(layout.get("w", 680.0))
        h = float(layout.get("h", 443.0))
        header_h = float(layout.get("header_h", 100.0))

        # Background + header panel
        self._wb_call(wb_uuid, "addShape", ("rectangle", 0.0, 0.0, w, h, self.UI_BG, self.UI_BG, 1.0), None)
        self._wb_call(wb_uuid, "addShape", ("rectangle", 0.0, 0.0, w, header_h, self.UI_PANEL, self.UI_PANEL, 1.0), None)

        # Bandeau score + tour + timer
        header = f"{self.p1_name}: {self.score_p1}    {self.p2_name}: {self.score_p2}"
        turn_str = f"Tour: {self.p1_name if self.turn == 1 else self.p2_name}" if self.state == "playing" else (
            "Prêt" if self.state == "idle" else "Terminé")
        timer_str = f"Temps: {self.time_left_s()}s" if self.state == "playing" else ""

        # On recrée si pas d’id connu
        if wb_uuid not in self._score_text_id:
            self._wb_call(wb_uuid, "addText", (header, 20.0, 18.0, self.UI_TEXT_LIGHT), f"{wb_uuid}:score")
        else:
            self._wb_call(wb_uuid, "setStringProperty", (self._score_text_id[wb_uuid], "text", header), None)

        if wb_uuid not in self._turn_text_id:
            self._wb_call(wb_uuid, "addText", (turn_str, 20.0, 52.0, self.UI_TEXT_LIGHT), f"{wb_uuid}:turn")
        else:
            self._wb_call(wb_uuid, "setStringProperty", (self._turn_text_id[wb_uuid], "text", turn_str), None)

        if wb_uuid not in self._timer_text_id:
            self._wb_call(wb_uuid, "addText", (timer_str, 20.0, 86.0, self.UI_TEXT_MUTED), f"{wb_uuid}:timer")
        else:
            self._wb_call(wb_uuid, "setStringProperty", (self._timer_text_id[wb_uuid], "text", timer_str), None)

        # Question + réponses
        if self.state == "idle":
            base_y = float(layout.get("q_panel_y", 120.0)) + 20.0
            self._wb_call(wb_uuid, "addText", ("Cliquez sur Start (dans Circle) pour lancer", 20.0, base_y, self.UI_TEXT_MUTED), None)
            return

        if self.state == "game_over":
            winner = self.p1_name if self.score_p1 >= self.TARGET_SCORE else self.p2_name
            base_y = float(layout.get("q_panel_y", 120.0)) + 20.0
            self._wb_call(wb_uuid, "addText", (f"Gagnant: {winner}", 20.0, base_y, self.UI_ACCENT), None)
            self._wb_call(wb_uuid, "addText", ("Reset (des deux joueurs) pour rejouer", 20.0, base_y + 40.0, self.UI_TEXT_MUTED), None)
            return

        if not self._current_question:
            base_y = float(layout.get("q_panel_y", 120.0)) + 20.0
            self._wb_call(wb_uuid, "addText", ("Pas de question disponible (API KO)", 20.0, base_y, "#F87171"), None)
            return

        # Question panel
        q_panel_x = float(layout.get("q_panel_x", 20.0))
        q_panel_y = float(layout.get("q_panel_y", 120.0))
        q_panel_w = float(layout.get("q_panel_w", w - 40.0))
        q_panel_h = float(layout.get("q_panel_h", 110.0))
        q_text_x = float(layout.get("q_text_x", q_panel_x + 12.0))
        q_text_y = float(layout.get("q_text_y", q_panel_y + 14.0))
        hint_y = float(layout.get("hint_y", q_panel_y + q_panel_h - 50.0))

        self._wb_call(wb_uuid, "addShape", ("rectangle", q_panel_x, q_panel_y, q_panel_w, q_panel_h, self.UI_PANEL, self.UI_PANEL, 1.0), None)

        # Wrap question to avoid overflow
        q_max_chars = self._estimate_chars_per_line(q_panel_w - 24.0)
        question_wrapped = self._wrap_text(self._current_question.question, max_chars=q_max_chars, max_lines=3)
        self._wb_call(wb_uuid, "addText", (question_wrapped, q_text_x, q_text_y, self.UI_TEXT_LIGHT), None)
        self._wb_call(wb_uuid, "addText", ("Répondre sur le contrôleur: A / B / C / D", q_text_x, hint_y, self.UI_TEXT_MUTED), None)

        for i, r in enumerate(rects):
            # Rectangle
            self._wb_call(wb_uuid, "addShape", ("rectangle", r.x, r.y, r.w, r.h, self.UI_CARD, self.UI_CARD_BORDER, 2.0), None)
            # Texte (wrap léger pour éviter les grosses réponses sur une seule ligne)
            choice_label = f"{chr(65+i)}) {self._current_question.choices[i]}"
            c_max_chars = self._estimate_chars_per_line(r.w - 28.0)
            choice_wrapped = self._wrap_text(choice_label, max_chars=c_max_chars, max_lines=3)
            self._wb_call(wb_uuid, "addText", (choice_wrapped, r.x + 14.0, r.y + 14.0, "#0F172A"), None)

    def _update_timer_texts(self, left_s: int) -> None:
        timer_str = f"Temps: {left_s}s"
        for wb_uuid in self._all_whiteboards():
            if wb_uuid in self._timer_text_id:
                self._wb_call(wb_uuid, "setStringProperty", (self._timer_text_id[wb_uuid], "text", timer_str), None)

    def _flash_choice(self, choice_index: int, *, correct: bool) -> None:
        # MVP: on recolore la forme (mais on ne garde pas l’id de la shape ici).
        # Pour rester simple, on ne fait pas d’animation; le prochain turn clear l’écran.
        del choice_index, correct

    # -------------------------
    # Whiteboard service callbacks
    # -------------------------

    def on_element_created(self, sender_uuid: str, element_id: int, token: Optional[str]) -> None:
        if not token:
            return
        if token == f"{sender_uuid}:timer":
            self._timer_text_id[sender_uuid] = element_id
        elif token == f"{sender_uuid}:score":
            self._score_text_id[sender_uuid] = element_id
        elif token == f"{sender_uuid}:turn":
            self._turn_text_id[sender_uuid] = element_id

    def on_action_result(self, succeeded: bool) -> None:
        if not succeeded:
            igs.error("Whiteboard a renvoyé actionResult=false")

    def on_whiteboard_size(self, sender_uuid: str, width: int, height: int) -> None:
        self._wb_size[sender_uuid] = (int(width), int(height))
        self._compute_layout_for_wb(sender_uuid)
