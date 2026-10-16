# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python): automatizare pe obiecte
# (Web / SAP / Desktop + Excel), rutine ca arbore de pasi.
# Echivalentul Studio RPR din versiunea C#, cu acelasi format de fisiere.
#
#   from rpr import Routine, RprEngine, RoutineStore, RepositoryStore
#   python -m rpr run "C:\...\rutina.rpr.json"      (rulare fara interfata)
# ============================================================

from .drivers.base import DriverProvider, ElementState, RprStepException, UiDriver
from .engine import RprEngine, matches_expected
from .host import AlertDecision, ErrorDecision, HeadlessRunHost, RunAlert, RunGuard, RunHost, RunResult
from .model import *  # noqa: F401,F403
from .storage import LegacyConverter, RepositoryStore, RoutineStore, RprPaths, RunLogExporter
from .variables import VariableStore

__version__ = "4.1"
