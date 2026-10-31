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
        self.routines_folder = ""          # 📂 Managerul de rutine: folderul citit la pornire (gol = rutine\\)
        self.library_path = ""             # 📚 biblioteca de obiecte deschisa ultima data (gol = obiecte.json implicit)
        # v4.14 (doar Python; C# ignora campurile): 📁 unde se salveaza + aspectul panourilor
        self.save_base_folder = ""         # folderul comun (gol = ca inainte)
        self.save_folders = {}             # {"libraries": ..., "results": ...} (gol = in folderul comun)
        self.layout = {}                   # latimea panourilor Studio, ca procent din fereastra

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
            s.routines_folder = str(d.get("routines_folder", ""))
            s.library_path = str(d.get("library_path", ""))
            s.save_base_folder = str(d.get("save_base_folder", "") or "")
            sf, lay = d.get("save_folders"), d.get("layout")
            s.save_folders = {str(k): str(v) for k, v in sf.items() if v} if isinstance(sf, dict) else {}
            s.layout = {str(k): float(v) for k, v in lay.items()
                        if isinstance(v, (int, float))} if isinstance(lay, dict) else {}
        except (OSError, ValueError):
            pass
        return s

    def save(self) -> None:
        try:   # campurile necunoscute (ex. scrise de alta versiune) raman in fisier
            with open(self.path(), encoding="utf-8-sig") as f:
                d = json.load(f)
            if not isinstance(d, dict):
                d = {}
        except (OSError, ValueError):
            d = {}
        d.update({"browser": self.browser, "headless": self.headless, "minimize_on_run": self.minimize_on_run,
                  "last_routine_path": self.last_routine_path, "routines_folder": self.routines_folder,
                  "library_path": self.library_path, "save_base_folder": self.save_base_folder,
                  "save_folders": dict(self.save_folders), "layout": dict(self.layout)})
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        from .. import locations
        locations.reset()

    def effective_routines_folder(self) -> str:
        return self.routines_folder.strip().strip('"') or RprPaths.routines()   # v4.14: sau folderul comun


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

    def mobile():   # v4.29: 📱 Android prin Appium (pachetul appium se importa doar la conectare)
        from .mobile import MobileDriver
        return MobileDriver(results_folder=RprPaths.output())

    provider.register(UiTechnology.Mobile, mobile)
