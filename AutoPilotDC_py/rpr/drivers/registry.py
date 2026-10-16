# -*- coding: utf-8 -*-
# Driverele disponibile in versiunea Python. Studio si rularea programata folosesc register_all().
from __future__ import annotations

import json
import os
from typing import Optional

from ..model import UiTechnology
from ..storage import RprPaths
from .base import DriverProvider


class StudioSettings:
    """Setarile Studio (acelasi fisier ca versiunea C#: %APPDATA%\\AutoPilotDC\\Studio\\studio-setari.json)."""

    def __init__(self):
        self.browser = "Edge"
        self.headless = False
        self.minimize_on_run = True
        self.last_routine_path = ""

    @staticmethod
    def path() -> str:
        os.makedirs(RprPaths.root, exist_ok=True)
        return os.path.join(RprPaths.root, "studio-setari.json")

    @classmethod
    def load(cls) -> "StudioSettings":
        s = cls()
        try:
            with open(cls.path(), encoding="utf-8-sig") as f:
                d = json.load(f)
            s.browser = str(d.get("browser", s.browser))
            s.headless = bool(d.get("headless", s.headless))
            s.minimize_on_run = bool(d.get("minimize_on_run", s.minimize_on_run))
            s.last_routine_path = str(d.get("last_routine_path", ""))
        except (OSError, ValueError):
            pass
        return s

    def save(self) -> None:
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump({"browser": self.browser, "headless": self.headless,
                           "minimize_on_run": self.minimize_on_run, "last_routine_path": self.last_routine_path},
                          f, ensure_ascii=False, indent=2)
        except OSError:
            pass


def register_all(provider: DriverProvider, settings: Optional[StudioSettings] = None) -> None:
    settings = settings or StudioSettings.load()

    def web():
        from .web import PlaywrightDriver, WebSettings
        ws = WebSettings(browser=settings.browser, headless=settings.headless,
                         # fiecare browser are profilul lui (Edge si Chrome nu pot folosi acelasi folder)
                         profile_folder=os.path.join(RprPaths.browser_profile(), settings.browser.lower()))
        return PlaywrightDriver(ws)

    provider.register(UiTechnology.Web, web)
    # Selenium nu e portat: obiectele "Web (Selenium)" ruleaza prin acelasi browser Playwright
    provider.register(UiTechnology.WebSelenium, lambda: provider.get(UiTechnology.Web))

    def desktop():
        from .desktop import DesktopDriver
        return DesktopDriver()

    def sap():
        from .sap import SapDriver
        return SapDriver()

    provider.register(UiTechnology.Desktop, desktop)
    provider.register(UiTechnology.Sap, sap)
