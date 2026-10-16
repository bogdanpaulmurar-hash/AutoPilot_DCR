# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# drivers/base.py — Contractul comun Web / Desktop / SAP
# Motorul nu stie cum se face un click in SAP sau in browser;
# cere driverului potrivit.
# ============================================================

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from ..model import Locator, RprAction, UiObject, UiTechnology


class RprStepException(Exception):
    """Eroare intr-un pas, cu mesaj pentru utilizator."""


class ElementNotFound(RprStepException):
    def __init__(self, obj: UiObject, timeout_ms: int, detail: str = ""):
        tried = "; ".join(str(l) for l in obj.active_locators)
        msg = f"Obiectul [{obj.name}] nu a fost gasit in {timeout_ms / 1000.0:.1f} s. Locatori incercati: {tried}"
        super().__init__(f"{msg}. Detalii: {detail}" if detail else msg)
        self.obj = obj


@dataclass(frozen=True)
class ElementState:
    exists: bool
    visible: bool = False
    enabled: bool = False
    text: str = ""
    value: str = ""
    used_locator: Optional[Locator] = None


NOT_FOUND = ElementState(False)


@dataclass(frozen=True)
class ActionRequest:
    action: RprAction
    target: Optional[UiObject]
    value: str
    timeout_ms: int
    direct_mode: bool
    output_folder: str


class UiDriver:
    """Un driver de interfata (o tehnologie). Metodele se apeleaza de pe firul motorului."""

    technology: UiTechnology = UiTechnology.Web
    display_name: str = ""

    def get_state(self, obj: UiObject, timeout_ms: int, stop: threading.Event) -> ElementState:
        """Cauta elementul (max timeout_ms). Nu arunca exceptie: NOT_FOUND daca nu exista."""
        raise NotImplementedError

    def execute(self, req: ActionRequest, stop: threading.Event) -> Optional[str]:
        """Executa actiunea. Returneaza valoarea citita (Citeste...) sau None. Arunca RprStepException."""
        raise NotImplementedError

    def highlight(self, obj: UiObject, duration_ms: int, stop: threading.Event) -> None:
        """Marcheaza vizual elementul (best effort, fara exceptii)."""

    def capture_error_screenshot(self, folder: str, name: str) -> Optional[str]:
        return None

    def close(self) -> None:
        pass


class UnavailableDriver(UiDriver):
    """Locul unui driver care nu e (inca) disponibil: orice folosire da un mesaj clar."""

    def __init__(self, technology: UiTechnology, reason: str):
        self.technology = technology
        self.display_name = str(technology)
        self._reason = reason

    def get_state(self, obj, timeout_ms, stop):
        raise RprStepException(self._reason)

    def execute(self, req, stop):
        raise RprStepException(self._reason)


class DriverProvider:
    """Furnizeaza driverul pentru o tehnologie (creat la prima folosire)."""

    def __init__(self, factories: Optional[Dict[UiTechnology, Callable[[], UiDriver]]] = None):
        self._factories = dict(factories or {})
        self._drivers: Dict[UiTechnology, UiDriver] = {}

    def register(self, technology: UiTechnology, factory: Callable[[], UiDriver]) -> None:
        self._factories[technology] = factory

    def get(self, technology: UiTechnology) -> UiDriver:
        technology = UiTechnology.parse(technology)
        d = self._drivers.get(technology)
        if d is None:
            factory = self._factories.get(technology)
            d = factory() if factory else UnavailableDriver(
                technology, f"Driverul pentru {technology} nu este disponibil in aceasta versiune.")
            self._drivers[technology] = d
        return d

    def close(self) -> None:
        for d in self._drivers.values():
            try:
                d.close()
            except Exception:
                pass
        self._drivers.clear()
