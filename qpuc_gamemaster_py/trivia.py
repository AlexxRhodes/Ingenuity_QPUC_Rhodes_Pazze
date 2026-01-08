from __future__ import annotations

from dataclasses import dataclass
import html
import random
from typing import List, Optional, Tuple

import requests


@dataclass(frozen=True)
class TriviaQuestion:
    question: str
    choices: List[str]
    correct_index: int


class OpenTDBClient:
    def __init__(self, *, session: Optional[requests.Session] = None, timeout_s: float = 10.0):
        self._session = session or requests.Session()
        self._timeout_s = timeout_s

    def fetch_many(self, *, amount: int = 10) -> List[TriviaQuestion]:
        # OpenTDB renvoie souvent des chaînes HTML-encodées.
        url = "https://opentdb.com/api.php"
        params = {
            "amount": int(amount),
            "type": "multiple",
        }
        resp = self._session.get(url, params=params, timeout=self._timeout_s)
        resp.raise_for_status()
        payload = resp.json()

        results = payload.get("results") or []
        out: List[TriviaQuestion] = []
        for item in results:
            q = html.unescape(item.get("question") or "").strip()
            correct = html.unescape(item.get("correct_answer") or "").strip()
            incorrect = [html.unescape(x).strip() for x in (item.get("incorrect_answers") or [])]
            choices = incorrect + [correct]
            random.shuffle(choices)
            try:
                correct_index = choices.index(correct)
            except ValueError:
                continue
            if not q or len(choices) != 4:
                continue
            out.append(TriviaQuestion(question=q, choices=choices, correct_index=correct_index))
        return out
