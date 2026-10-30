# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# legacy.py — Executa pasii vechi (pe coordonate) dintr-o rutina RPR.
# Aceeasi logica ca PlayerEngine._exec din aplicatia principala.
# ============================================================

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

_KEY_MAP = {
    "ctrl": "ctrl", "shift": "shift", "alt": "alt",
    "enter": "enter", "return": "enter", "tab": "tab",
    "space": "space", "backspace": "backspace", "delete": "delete",
    "esc": "escape", "escape": "escape",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end", "pageup": "pageup", "pagedown": "pagedown",
    **{f"f{i}": f"f{i}" for i in range(1, 13)},
    "insert": "insert", "capslock": "capslock", "numlock": "numlock",
    "win": "win", "winleft": "winleft", "winright": "winright",
}


def _pynput_combo(mods, final_key) -> bool:
    try:
        import pynput.keyboard as pk
        kb = pk.Controller()
        mod_keys = {"ctrl": pk.Key.ctrl, "shift": pk.Key.shift, "alt": pk.Key.alt, "win": pk.Key.cmd}
        held = [mod_keys[m] for m in mods if m in mod_keys]
        for m in held:
            kb.press(m)
        key = final_key if len(str(final_key)) == 1 else getattr(pk.Key, final_key, final_key)
        kb.press(key)
        kb.release(key)
        for m in reversed(held):
            kb.release(m)
        return True
    except Exception:
        return False


def execute_legacy_step(step: Dict[str, Any]) -> Tuple[bool, str]:
    """Executa un pas pe coordonate (dict cu chei snake_case). Returneaza (succes, eroare)."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
    except ImportError:
        return False, "Lipseste pachetul pyautogui. Ruleaza INSTALEAZA.bat din folderul aplicatiei."

    g = lambda k, d=None: step.get(k, d)  # noqa: E731
    try:
        t = g("step_type", "")
        x, y = int(g("x", 0) or 0), int(g("y", 0) or 0)
        if t in ("CLICK", "DBLCLICK", "RIGHTCLICK"):
            btn = g("button", "left") if g("button") in ("left", "right", "middle") else "left"
            if t == "DBLCLICK" or g("click_type") == "double":
                pyautogui.doubleClick(x, y, button=btn)
            elif t == "RIGHTCLICK" or g("click_type") == "right":
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y, button=btn)
        elif t == "MOVE":
            pyautogui.moveTo(x, y, duration=0.15)
        elif t == "SCROLL":
            pyautogui.scroll(int(g("scroll_dy", 0) or 0), x=x, y=y)
        elif t == "KEY":
            combo = g("key_combo", "") or ""
            parts = combo.split("+") if "+" in combo else [combo]
            mods = [_KEY_MAP.get(p.lower(), p.lower()) for p in parts[:-1]]
            key = parts[-1]
            if len(key) == 1 and ord(key) > 127:      # diacritice: pynput
                _pynput_combo(mods, key)
            else:
                mapped = _KEY_MAP.get(key.lower(), key.lower())
                try:
                    pyautogui.hotkey(*mods, mapped) if mods else pyautogui.press(mapped)
                except Exception:
                    _pynput_combo(mods, mapped)
        elif t == "TYPE":
            txt = g("text_input", "") or ""
            if any(ord(c) > 127 for c in txt):
                try:
                    import pynput.keyboard as pk
                    kb = pk.Controller()
                    for ch in txt:
                        kb.press(ch)
                        kb.release(ch)
                        time.sleep(0.04)
                except Exception:
                    pyautogui.typewrite(txt, interval=0.04)
            else:
                pyautogui.typewrite(txt, interval=0.04)
        elif t == "DELAY":
            time.sleep(max(float(g("delay_before", 0) or 0), 0.1))
        return True, ""
    except Exception as ex:  # noqa: BLE001
        return False, str(ex)


# ─────────────────────────────────────────────────────────────
# v4.16: inregistrarea pe ecran (fostul tab Recorder) -> pasi Studio
# ─────────────────────────────────────────────────────────────
_CHAR_NAMES = {"space": " "}


def _typed_char(step: Dict[str, Any]):
    """Caracterul scris de o tasta simpla (litera, cifra, semn; Shift+litera), altfel None."""
    if str(step.get("step_type", "")).upper() != "KEY":
        return None
    combo = str(step.get("key_combo") or "")
    if combo.startswith("Shift+") and len(combo) == 7:
        combo = combo[6:].upper()   # pynput da de obicei deja "B"; "Shift+b" -> "B"
    if combo in _CHAR_NAMES:
        return _CHAR_NAMES[combo]
    return combo if len(combo) == 1 and combo.isprintable() else None


def merge_typing(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tastele simple apasate una dupa alta in aceeasi fereastra devin un singur pas "Scrie text"."""
    out: List[Dict[str, Any]] = []
    for s in steps:
        ch = _typed_char(s)
        prev = out[-1] if out else None
        if ch is not None and prev is not None and prev.get("_typing") \
                and prev.get("window_process", "") == s.get("window_process", "") \
                and float(s.get("delay_before") or 0) < 3.0:
            prev["text_input"] += ch
            prev["description"] = "Scrie: " + prev["text_input"]
            continue
        s = dict(s)
        if ch is not None:
            s.update(step_type="TYPE", text_input=ch, key_combo="", description="Scrie: " + ch, _typing=True)
        out.append(s)
    for s in out:
        s.pop("_typing", None)
    return out


def recorded_to_nodes(steps: List[Dict[str, Any]]) -> list:
    """Pasii inregistrati (dict-uri StepModel) -> pasi Studio "pe ecran" (LegacyStepNode), cu asteptarile lor."""
    from .storage import LegacyConverter
    return LegacyConverter.convert("Inregistrare", merge_typing(steps)).steps
