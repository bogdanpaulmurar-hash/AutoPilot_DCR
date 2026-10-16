# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# legacy.py — Executa pasii vechi (pe coordonate) dintr-o rutina RPR.
# Aceeasi logica ca PlayerEngine._exec din aplicatia principala.
# ============================================================

from __future__ import annotations

import time
from typing import Any, Dict, Tuple

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
