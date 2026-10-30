# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🎥 Inregistrare video a ecranului (din capturi de ecran)
#
# Format .apvid = arhiva zip:
#   manifest.json   — dimensiuni, cadre [timp, fisier], cursor, click-uri, marcaje, editari
#   frames/*.webp   — capturi de ecran comprimate, salvate DOAR cand ecranul se schimba
# Cursorul si click-urile se salveaza separat (se deseneaza la redare), deci un ecran static
# nu ocupa loc chiar daca mouse-ul se misca. Editarile (taiere, texte, zone ascunse, pauze
# scurtate) sunt nedistructive: se pastreaza in manifest si se aplica la redare / export.
# Export: GIF (mereu) si MP4 (daca e instalat opencv-python).
# ============================================================

from __future__ import annotations

import ctypes
import datetime as _dt
import io
import json
import os
import re
import threading
import time
import zipfile
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageGrab

EXT = ".apvid"
_SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC", "video.json")


def _legacy_folder() -> str:
    home = os.path.expanduser("~")
    videos = os.path.join(home, "Videos")
    return os.path.join(videos if os.path.isdir(videos) else home, "AutoPilotDC")


def _default_folder() -> str:
    """v4.14: <folderul comun>\filme daca e setat in 🌐 Setari Studio → 📁 Unde se salveaza, altfel Videos."""
    try:
        from rpr import locations
        common = locations.common("videos")
        if common:
            return common
    except Exception:  # noqa: BLE001
        pass
    return _legacy_folder()


# v4.14: cu ce se deschid filmele (🎬, linkurile din Excel, dublu-click pe .apvid)
PLAYER_BUILTIN = ""            # playerul / editorul AutoPilot
PLAYER_SYSTEM = "system"       # aplicatia implicita din Windows pentru MP4 (filmul se exporta intai)


# ─────────────────────────────────────────────────────────────
# 1. Setari
# ─────────────────────────────────────────────────────────────
@dataclass
class VideoSettings:
    folder: str = field(default_factory=_default_folder)
    fps: int = 4                      # capturi pe secunda (2-10); 4 = fluent pentru proceduri
    scale: float = 0.75               # marimea cadrelor fata de ecran (0.5 = mic, 1.0 = original)
    quality: int = 60                 # calitate WebP (30-90)
    area: str = "window"              # window = doar fereastra aleasa (implicit); primary = ecranul principal; all = toate
    record_on_run: bool = False       # porneste singur la rularea unei rutine (Studio / Recorder)
    per_row: bool = False             # in bucla Excel: cate un video pentru fiecare rand
    on_schedule: bool = False         # si la rularile programate
    show_cursor: bool = True
    show_clicks: bool = True
    max_minutes: int = 60             # protectie: opreste dupa atatea minute
    idle_compress_s: float = 2.0      # la redare / export: pauzele mai lungi se scurteaza la atat (0 = nu)
    intro_outro: bool = True          # v4.16: filmele rularilor incep cu o introducere si se termina cu o iesire
    intro_s: float = 3.0              # cat dureaza introducerea (titlu, data)
    outro_s: float = 4.0              # cat dureaza iesirea (rezultat, durata)
    tail_s: float = 2.0               # dupa ultimul pas se mai filmeaza atat (rezultatul ultimului pas)
    player: str = PLAYER_BUILTIN      # "" = AutoPilot, "system" = aplicatia din Windows, altfel calea unui .exe

    @classmethod
    def load(cls) -> "VideoSettings":
        s = cls()
        try:
            with open(_SETTINGS, encoding="utf-8") as f:
                d = json.load(f)
            for k, v in d.items():
                if hasattr(s, k):
                    setattr(s, k, type(getattr(s, k))(v))
        except (OSError, ValueError, TypeError):
            pass
        s.fps = max(1, min(10, int(s.fps)))
        s.scale = max(0.3, min(1.0, float(s.scale)))
        s.quality = max(20, min(95, int(s.quality)))
        s.intro_s = max(0.0, min(15.0, float(s.intro_s)))
        s.outro_s = max(0.0, min(15.0, float(s.outro_s)))
        s.tail_s = max(0.0, min(15.0, float(s.tail_s)))
        # folderul implicit nu se "ingheata" in fisier: urmeaza folderul comun cand acesta se schimba
        if not s.folder.strip() or os.path.normcase(os.path.normpath(s.folder)) == \
                os.path.normcase(os.path.normpath(_legacy_folder())):
            s.folder = _default_folder()
        return s

    def save(self) -> None:
        os.makedirs(os.path.dirname(_SETTINGS), exist_ok=True)
        d = asdict(self)
        if os.path.normcase(os.path.normpath(self.folder or ".")) in {
                os.path.normcase(os.path.normpath(_default_folder())),
                os.path.normcase(os.path.normpath(_legacy_folder()))}:
            d["folder"] = ""
        with open(_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)


# ─────────────────────────────────────────────────────────────
# 2. Ecran / mouse (Win32)
# ─────────────────────────────────────────────────────────────
try:
    _user32 = ctypes.windll.user32
except AttributeError:   # pragma: no cover
    _user32 = None


def screen_bbox(area: str) -> Tuple[int, int, int, int]:
    if _user32 is None:
        return 0, 0, 1280, 800
    if area == "all":
        x, y = _user32.GetSystemMetrics(76), _user32.GetSystemMetrics(77)
        return x, y, x + _user32.GetSystemMetrics(78), y + _user32.GetSystemMetrics(79)
    return 0, 0, _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)


def _cursor() -> Tuple[int, int]:
    class P(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = P()
    if _user32 is not None:
        _user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _mouse_down() -> bool:
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(0x01) & 0x8000 or _user32.GetAsyncKeyState(0x02) & 0x8000)


# ── o singura fereastra (nimic altceva de pe ecran nu ajunge in film) ──
from ctypes import wintypes  # noqa: E402


def _dpi_aware_thread():
    """Coordonate in pixeli reali pe firul curent (altfel Windows le scaleaza la 125% / 150%)."""
    try:
        _user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))   # PER_MONITOR_AWARE_V2
    except Exception:
        pass


def window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Marginile vizibile ale ferestrei (fara bordura invizibila de 7 px din Windows 10/11)."""
    if _user32 is None or not hwnd or not _user32.IsWindow(hwnd):
        return None
    r = wintypes.RECT()
    try:
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r)) == 0:
            return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    if _user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(r)):
        return r.left, r.top, r.right, r.bottom
    return None


def window_title(hwnd: int) -> str:
    if _user32 is None or not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetWindowTextW(wintypes.HWND(hwnd), buf, 256)
    return buf.value


def root_window_at(x: int, y: int) -> int:
    if _user32 is None:
        return 0
    _user32.WindowFromPoint.restype = wintypes.HWND
    h = _user32.WindowFromPoint(wintypes.POINT(x, y))
    _user32.GetAncestor.restype = wintypes.HWND
    return int(_user32.GetAncestor(h, 2) or 0) if h else 0


def capture_window(hwnd: int) -> Optional[Image.Image]:
    """Doar continutul ferestrei (PrintWindow), chiar daca alta fereastra trece peste ea."""
    if _user32 is None or not _user32.IsWindow(hwnd) or _user32.IsIconic(hwnd):
        return None
    gdi = ctypes.windll.gdi32
    full = wintypes.RECT()
    _user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(full))
    w, h = full.right - full.left, full.bottom - full.top
    if w <= 0 or h <= 0:
        return None
    hdc_screen = _user32.GetDC(0)
    hdc = gdi.CreateCompatibleDC(hdc_screen)
    bmp = gdi.CreateCompatibleBitmap(hdc_screen, w, h)
    old = gdi.SelectObject(hdc, bmp)
    try:
        if not _user32.PrintWindow(wintypes.HWND(hwnd), hdc, 2):   # PW_RENDERFULLCONTENT
            return None

        class BMI(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                        ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16),
                        ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                        ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
                        ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32),
                        ("bmiColors", ctypes.c_uint32 * 3)]
        bmi = BMI()
        bmi.biSize = 40
        bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = w, -h, 1, 32
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
        img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1).copy()
    finally:
        gdi.SelectObject(hdc, old)
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(hdc)
        _user32.ReleaseDC(0, hdc_screen)
    vis = window_rect(hwnd)   # taiem bordura invizibila
    if vis:
        box = (vis[0] - full.left, vis[1] - full.top, vis[2] - full.left, vis[3] - full.top)
        if 0 <= box[0] < box[2] <= w and 0 <= box[1] < box[3] <= h:
            img = img.crop(box)
    return img


def foreground_root() -> int:
    if _user32 is None:
        return 0
    _user32.GetForegroundWindow.restype = wintypes.HWND
    h = _user32.GetForegroundWindow()
    _user32.GetAncestor.restype = wintypes.HWND
    return int(_user32.GetAncestor(h, 2) or 0) if h else 0


def _fit(img: Image.Image, size) -> Tuple[Image.Image, float, int, int]:
    """Imaginea incadrata (fara deformare) intr-un cadru de marime fixa; (cadru, scara, dx, dy)."""
    W, H = size
    if img.size == (W, H):
        return img, 1.0, 0, 0
    k = min(W / img.width, H / img.height)
    w, h = max(1, int(img.width * k)), max(1, int(img.height * k))
    canvas = Image.new("RGB", (W, H), (24, 24, 32))
    dx, dy = (W - w) // 2, (H - h) // 2
    canvas.paste(img.resize((w, h), Image.BILINEAR), (dx, dy))
    return canvas, k, dx, dy


def safe_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", text).strip(" ._") or "video"


# ─────────────────────────────────────────────────────────────
# 3. Inregistrare
# ─────────────────────────────────────────────────────────────
class ScreenRecorder:
    """Inregistreaza ecranul pe un fir separat. start() -> ... -> stop() returneaza calea fisierului."""

    def __init__(self, settings: Optional[VideoSettings] = None):
        self.s = settings or VideoSettings.load()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._lock = threading.Lock()
        self._zip: Optional[zipfile.ZipFile] = None
        self.path = ""
        self._m: Dict[str, Any] = {}
        self._t0 = 0.0
        self._paused_total = 0.0
        self._pause_started = 0.0
        self.on_stopped: Optional[Callable[[str], None]] = None
        self.last_error = ""
        self.hwnd = 0           # >0 = se inregistreaza doar aceasta fereastra
        self.follow = False     # True = fereastra activa (cea in care lucreaza rutina), schimbata din mers
        self.ignore_hwnds = set()   # ferestre care nu se inregistreaza niciodata (ex. AutoPilot la rulare)
        self._offset = 0.0      # durata introducerii: cadrele reale incep dupa ea
        self._outro: Optional[List[str]] = None

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def elapsed(self) -> float:
        if not self.active:
            return 0.0
        now = time.monotonic()
        paused = self._paused_total + ((now - self._pause_started) if self._paused.is_set() else 0.0)
        return max(0.0, now - self._t0 - paused) + self._offset

    def start(self, title: str = "Inregistrare", folder: str = "", hwnd: int = 0, follow: bool = False,
              intro: Optional[List[str]] = None) -> str:
        """hwnd > 0: doar fereastra respectiva; follow=True: mereu doar fereastra activa.
        In ambele cazuri restul ecranului (alte aplicatii, bara de activitati) nu apare in film.
        intro: randurile introducerii (data, ce se ruleaza); None = fara introducere."""
        if self.active:
            return self.path
        folder = folder or getattr(self, "folder", "") or self.s.folder
        self.folder = folder            # split() pastreaza acelasi folder (ex. folderul filmelor rutinei)
        os.makedirs(folder, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(folder, f"{safe_name(title)}_{stamp}{EXT}")
        self.hwnd = hwnd or self.hwnd
        self.follow = follow or self.follow
        bbox = window_rect(self.hwnd) if self.hwnd and not self.follow else None
        if bbox is None:
            if not self.follow:
                self.hwnd = 0
            bbox = screen_bbox("all" if self.s.area == "all" else "primary")
        w = int((bbox[2] - bbox[0]) * self.s.scale)
        h = int((bbox[3] - bbox[1]) * self.s.scale)
        self._m = {"version": 1, "title": title, "created": _dt.datetime.now().isoformat(timespec="seconds"),
                   "size": [w, h], "scale": self.s.scale, "origin": [bbox[0], bbox[1]], "fps": self.s.fps,
                   "window": window_title(self.hwnd) if self.hwnd else "",
                   "duration": 0.0, "frames": [], "cursor": [], "clicks": [], "markers": [],
                   "edits": {"trim": None, "cuts": [], "captions": [], "blur": [],
                             "idle": self.s.idle_compress_s}}
        self._zip = zipfile.ZipFile(self.path, "w", zipfile.ZIP_STORED)
        self._offset = 0.0
        self._outro = None
        if intro is not None and self.s.intro_outro and self.s.intro_s > 0:
            self._offset = round(float(self.s.intro_s), 2)
            self._write_card("frames/intro.webp", 0.0, title_card((w, h), title, intro, "intro"))
            self._m["intro"] = [0.0, self._offset]
            self._m["markers"].append([0.0, "▶ " + str(title)[:110]])
        self._stop.clear()
        self._paused.clear()
        self._paused_total = 0.0
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._run, args=(bbox,), daemon=True, name="ScreenRecorder")
        self._thread.start()
        return self.path

    def pause(self, on: bool = True):
        if on and not self._paused.is_set():
            self._pause_started = time.monotonic()
            self._paused.set()
        elif not on and self._paused.is_set():
            self._paused_total += time.monotonic() - self._pause_started
            self._paused.clear()

    def marker(self, text: str):
        """Un marcaj in film (pas, rand Excel) — apare ca un capitol in editor."""
        if self.active:
            with self._lock:
                self._m["markers"].append([round(self.elapsed(), 2), str(text)[:120]])

    def _write_card(self, name: str, t: float, img: Image.Image):
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "WEBP", quality=max(70, self.s.quality), method=4)
        self._zip.writestr(name, buf.getvalue())
        with self._lock:
            self._m["frames"].append([round(t, 2), name])

    def stop(self, outro: Optional[List[str]] = None) -> str:
        """outro: randurile iesirii (rezultat, durata); None = fara iesire.
        Inainte de oprire se salveaza inca un cadru: ecranul exact de la final (ultimul pas)."""
        if self._thread is None:
            return ""
        self._outro = outro
        self._stop.set()
        self._thread.join(timeout=10)
        self._thread = None
        path = self.path
        if self.on_stopped and path:
            try:
                self.on_stopped(path)
            except Exception:
                pass
        return path

    def split(self, title: str, outro: Optional[List[str]] = None, intro: Optional[List[str]] = None) -> str:
        """Inchide filmul curent si incepe altul (ex. un video pentru fiecare rand Excel)."""
        old = self.stop(outro) if self.active else ""
        self.start(title, intro=intro)
        return old

    def _grab(self, bbox, target: int, size) -> Optional[Image.Image]:
        """O captura: fereastra urmarita (target) sau zona bbox; None = nu se poate acum."""
        if target:
            img = capture_window(target)   # doar fereastra (nu ce e peste / langa ea)
            return _fit(img, size)[0] if img is not None else None
        return ImageGrab.grab(bbox=bbox, all_screens=self.s.area == "all")

    def _run(self, bbox):
        s = self.s
        period = 1.0 / max(1, s.fps)
        prev_thumb = None
        last_saved_t = -999.0
        n = 0
        down_before = False
        last_cur = None
        x0, y0 = bbox[0], bbox[1]
        _dpi_aware_thread()
        size = tuple(self._m["size"])
        last_journal = time.monotonic()
        try:
            while not self._stop.is_set():
                tick = time.monotonic()
                if self._paused.is_set():
                    time.sleep(0.1)
                    continue
                t = round(self.elapsed(), 2)
                if t > s.max_minutes * 60:
                    break
                rect = bbox
                target = self.hwnd
                if self.follow:   # fereastra in care lucreaza rutina acum
                    fg = foreground_root()
                    if fg and fg not in self.ignore_hwnds:
                        self.hwnd = fg
                    target = self.hwnd
                if target:   # fereastra se poate muta / redimensiona: urmarim marginile ei
                    rect = window_rect(target)
                    if rect is None:
                        if self.follow:
                            time.sleep(period)
                            continue
                        break   # fereastra a fost inchisa
                    x0, y0 = rect[0], rect[1]
                # mouse: pozitie (daca s-a miscat) + click-uri; in afara ferestrei = ascuns (-1)
                cx, cy = _cursor()
                rw, rh = max(1, rect[2] - rect[0]), max(1, rect[3] - rect[1])
                k = min(size[0] / rw, size[1] / rh)
                dx, dy = (size[0] - int(rw * k)) // 2, (size[1] - int(rh * k)) // 2
                inside = rect[0] <= cx < rect[2] and rect[1] <= cy < rect[3]
                cur = [t, int((cx - x0) * k) + dx, int((cy - y0) * k) + dy] if inside else [t, -1, -1]
                if last_cur is None or cur[1:] != last_cur[1:]:
                    with self._lock:
                        self._m["cursor"].append(cur)
                    last_cur = cur
                down = _mouse_down()
                if down and not down_before and inside:
                    with self._lock:
                        self._m["clicks"].append(cur)
                down_before = down
                # ecran: salvam cadrul doar daca s-a schimbat (sau la 15 s, cadru de siguranta)
                try:
                    img = self._grab(bbox, target, size)
                    if img is None:                   # minimizata: pastram ultimul cadru
                        time.sleep(period)
                        continue
                except Exception as ex:  # noqa: BLE001 — ecran blocat (Ctrl+Alt+Del), sesiune RDP minimizata
                    self.last_error = str(ex)
                    time.sleep(period)
                    continue
                thumb = img.resize((max(1, img.width // 8), max(1, img.height // 8)), Image.BILINEAR).convert("L")
                # schimbare reala = pixeli care difera vizibil (cursorul de text care clipeste nu conteaza)
                changed = prev_thumb is None or ImageChops.difference(thumb, prev_thumb).point(
                    lambda v: 255 if v > 24 else 0).getbbox() is not None
                if changed or t - last_saved_t > 15:
                    frame = _fit(img, size)[0]
                    buf = io.BytesIO()
                    frame.convert("RGB").save(buf, "WEBP", quality=s.quality, method=4)
                    n += 1
                    name = f"frames/{n:06d}.webp"
                    self._zip.writestr(name, buf.getvalue())
                    with self._lock:
                        self._m["frames"].append([t, name])
                    last_saved_t = t
                    prev_thumb = thumb
                if time.monotonic() - last_journal > 10:   # 💾 jurnal pentru recuperare (aplicatie blocata, PC oprit)
                    self._write_journal()
                    last_journal = time.monotonic()
                # ritmul de captura (capturile mari pot dura mai mult decat perioada)
                time.sleep(max(0.01, period - (time.monotonic() - tick)))
        finally:
            end = round(self.elapsed(), 2)
            # ultimul cadru = ecranul exact de la oprire (altfel rezultatul ultimului pas se putea pierde)
            if self._stop.is_set():
                try:
                    img = self._grab(bbox, self.hwnd if (self.hwnd or self.follow) else 0, size)
                    if img is not None:
                        n += 1
                        self._write_card(f"frames/{n:06d}.webp", end, _fit(img, size)[0])
                except Exception as ex:  # noqa: BLE001
                    self.last_error = str(ex)
            duration = end
            outro = self._outro
            if outro is not None and s.intro_outro and s.outro_s > 0:
                # ultimul ecran ramane o secunda, apoi iesirea
                t_out = round(end + 1.0, 2)
                try:
                    self._write_card("frames/outro.webp", t_out,
                                     title_card(size, self._m.get("title", ""), outro, "outro"))
                    self._m["outro"] = [t_out, round(t_out + s.outro_s, 2)]
                    with self._lock:
                        self._m["markers"].append([t_out, "■ " + (outro[0] if outro else "")[:110]])
                    duration = round(t_out + s.outro_s, 2)
                except Exception as ex:  # noqa: BLE001
                    self.last_error = str(ex)
            # finalul (ultimul pas + iesirea) nu se scurteaza la redare, chiar daca ecranul nu se mai schimba
            self._m["hold"] = [round(max(0.0, end - max(1.0, s.tail_s)), 2), duration]
            with self._lock:
                self._m["duration"] = duration
                self._zip.writestr("manifest.json", json.dumps(self._m, ensure_ascii=False))
            self._zip.close()
            self._zip = None
            try:
                os.remove(self.path + JOURNAL_EXT)   # filmul e complet: jurnalul nu mai trebuie
            except OSError:
                pass

    def _write_journal(self):
        """Cronologia de pana acum langa film. Daca filmul ramane neterminat, recover() il reface din ea."""
        try:
            with self._lock:
                data = json.dumps(dict(self._m, duration=round(self.elapsed(), 2)), ensure_ascii=False)
            tmp = self.path + JOURNAL_EXT + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, self.path + JOURNAL_EXT)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────
# 4. Redare / editare / export
# ─────────────────────────────────────────────────────────────
def _is_emoji(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x1F000 or 0x2300 <= o <= 0x23FF or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or o == 0xFE0F


def _runs(text: str):
    """Textul impartit in bucati normale / emoji (emoji se deseneaza cu fontul Segoe UI Emoji)."""
    out, cur, emo = [], "", None
    for ch in text:
        e = _is_emoji(ch)
        if emo is None or e == emo:
            cur += ch
        else:
            out.append((cur, emo))
            cur = ch
        emo = e
    if cur:
        out.append((cur, bool(emo)))
    return out


def _emoji_font(size: int):
    try:
        return ImageFont.truetype("seguiemj.ttf", size)
    except OSError:
        return None


def _text_len(draw, text, font, efont) -> float:
    return sum(draw.textlength(t, font=efont if (e and efont) else font) for t, e in _runs(text))


def _draw_text(draw, xy, text, font, efont, fill):
    x, y = xy
    for t, e in _runs(text):
        f = efont if (e and efont) else font
        if e and efont:
            draw.text((x, y), t.replace("\ufe0f", ""), font=f, embedded_color=True)
        else:
            draw.text((x, y), t, font=f, fill=fill)
        x += draw.textlength(t, font=f)


def _font(size: int):
    for name in ("segoeuib.ttf", "segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)   # Pillow >= 10.1: font scalabil
    except TypeError:
        return ImageFont.load_default()


JOURNAL_EXT = ".jurnal.json"


def title_card(size, title: str, lines: List[str], kind: str = "intro") -> Image.Image:
    """Cadrul de introducere / iesire: fundal inchis, numele rutinei mare, randurile dedesubt."""
    w, h = int(size[0]), int(size[1])
    img = Image.new("RGB", (w, h), (24, 28, 40))
    d = ImageDraw.Draw(img)
    accent = (0, 150, 136) if kind == "intro" else (90, 110, 160)
    if kind == "outro" and lines and lines[0].startswith(("❌", "⛔", "✕")):
        accent = (198, 40, 40)
    d.rectangle([0, 0, w, max(6, h // 60)], fill=accent)
    d.rectangle([0, h - max(6, h // 60), w, h], fill=accent)
    big, mid, small = _font(max(18, h // 14)), _font(max(14, h // 26)), _font(max(12, h // 36))
    efont = _emoji_font(max(14, h // 26))
    y = h // 4
    _draw_text(d, (w // 12, y), "AutoPilot DC", small, None, (150, 160, 180))
    y += int(h / 36 * 1.8)
    for ln in _wrap(d, str(title), big, w - w // 6)[:2]:
        _draw_text(d, (w // 12, y), ln, big, None, (240, 244, 250))
        y += int(h / 14 * 1.25)
    y += h // 40
    for text in lines:
        for ln in _wrap(d, str(text), mid, w - w // 6, efont)[:2]:
            _draw_text(d, (w // 12, y), ln, mid, efont, (200, 210, 225))
            y += int(h / 26 * 1.5)
    return img


def recover(path: str) -> bool:
    """Reface un film neterminat (aplicatia s-a blocat / PC-ul s-a oprit in timpul inregistrarii):
    cadrele scrise deja se citesc direct din fisier, cronologia din jurnalul de langa el (sau, fara jurnal,
    cadrele primesc timpi la rand). Originalul ramane ca .stricat."""
    import struct
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return False
    frames: Dict[str, bytes] = {}
    i = raw.find(b"PK\x03\x04")
    while 0 <= i < len(raw) - 30:
        _sig, _ver, flag, method, _t, _d, _crc, csize, _usize, nlen, xlen = struct.unpack("<IHHHHHIIIHH", raw[i:i + 30])
        name = raw[i + 30:i + 30 + nlen].decode("utf-8", "replace")
        start = i + 30 + nlen + xlen
        if method != 0 or flag & 0x08 or start + csize > len(raw):
            break                               # cadru taiat la jumatate: ne oprim aici
        if name.startswith("frames/"):
            frames[name] = raw[start:start + csize]
        i = raw.find(b"PK\x03\x04", start + csize)
    if not frames:
        return False
    m = None
    try:
        with open(path + JOURNAL_EXT, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        pass
    if m:
        m["frames"] = [fr for fr in m.get("frames", []) if fr[1] in frames]
    else:
        m = {"version": 1, "title": os.path.basename(path), "fps": 4, "cursor": [], "clicks": [], "markers": [],
             "edits": {"trim": None, "cuts": [], "captions": [], "blur": [], "idle": 2.0}}
        m["frames"] = [[round(k * 0.5, 2), n] for k, n in enumerate(sorted(frames))]
        try:
            from PIL import Image as _Img
            first = _Img.open(io.BytesIO(frames[sorted(frames)[0]]))
            m["size"] = [first.width, first.height]
        except Exception:  # noqa: BLE001
            m["size"] = [1280, 720]
    known = {fr[1] for fr in m["frames"]}
    last_t = m["frames"][-1][0] if m["frames"] else 0.0
    for n in sorted(frames):   # cadre scrise dupa ultimul jurnal
        if n not in known:
            last_t = round(last_t + 0.5, 2)
            m["frames"].append([last_t, n])
    m["duration"] = max(float(m.get("duration") or 0), m["frames"][-1][0] if m["frames"] else 0.0)
    m["title"] = str(m.get("title", "")) + " (recuperat)"
    tmp = path + ".recuperat.tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
        for _t, n in m["frames"]:
            z.writestr(n, frames[n])
        z.writestr("manifest.json", json.dumps(m, ensure_ascii=False))
    try:
        os.replace(path, path + ".stricat")
    except OSError:
        pass
    os.replace(tmp, path)
    try:
        os.remove(path + JOURNAL_EXT)
    except OSError:
        pass
    return True


class VideoFile:
    """Un film .apvid deschis: cadre la cerere, cronologie dupa editari, compunere (cursor, texte, blur)."""

    def __init__(self, path: str):
        self.path = path
        self._zip = None
        try:
            self._zip = zipfile.ZipFile(path, "r")
            self._zip.getinfo("manifest.json")
        except (zipfile.BadZipFile, KeyError):
            if self._zip is not None:
                self._zip.close()      # Windows: fisierul trebuie eliberat inainte de refacere
            if not recover(path):      # film neterminat: il refacem din cadrele scrise deja
                raise
            self._zip = zipfile.ZipFile(path, "r")
        self.m: Dict[str, Any] = json.loads(self._zip.read("manifest.json").decode("utf-8"))
        self.m.setdefault("edits", {})
        e = self.m["edits"]
        e.setdefault("trim", None)
        e.setdefault("cuts", [])
        e.setdefault("captions", [])
        e.setdefault("blur", [])
        e.setdefault("idle", 0.0)
        self._cache: Dict[str, Image.Image] = {}
        self._frame_times = [f[0] for f in self.m["frames"]]
        self.timeline: List[Tuple[float, float]] = []
        self.rebuild()

    @property
    def size(self) -> Tuple[int, int]:
        return tuple(self.m["size"])

    @property
    def duration(self) -> float:
        return float(self.m.get("duration") or (self._frame_times[-1] if self._frame_times else 0.0))

    @property
    def edits(self) -> Dict[str, Any]:
        return self.m["edits"]

    def close(self):
        try:
            self._zip.close()
        except Exception:
            pass

    # ── cronologie ──
    def kept(self, t: float) -> bool:
        e = self.edits
        if e.get("trim"):
            a, b = e["trim"]
            if t < a or t > b:
                return False
        return not any(a <= t < b for a, b in e.get("cuts", []))

    def rebuild(self, step: float = 0.0):
        """Lista (timp_iesire, timp_sursa) dupa taieri si scurtarea pauzelor."""
        fps = max(1, int(self.m.get("fps", 4)))
        step = step or 1.0 / fps
        idle = float(self.edits.get("idle") or 0.0)
        events = sorted(set(self._frame_times) | {c[0] for c in self.m.get("cursor", [])}
                        | {c[0] for c in self.m.get("clicks", [])}
                        | {c["t0"] for c in self.edits.get("captions", [])})
        # introducerea, finalul (ultimul pas) si iesirea raman intregi (nu sunt "pauze")
        protect = [seg for seg in (self.m.get("intro"), self.m.get("hold"), self.m.get("outro")) if seg]
        out, ot, t = [], 0.0, 0.0
        last_event = 0.0
        ei = 0
        dur = self.duration
        while t <= dur + 1e-6:
            while ei < len(events) and events[ei] <= t:
                last_event = events[ei]
                ei += 1
            if self.kept(t):
                idle_now = idle > 0 and (t - last_event) > idle and not self._caption_at(t) \
                    and not any(a <= t <= b for a, b in protect)
                if not idle_now:
                    out.append((round(ot, 3), round(t, 3)))
                    ot += step
            t += step
        self.timeline = out or [(0.0, 0.0)]

    @property
    def out_duration(self) -> float:
        return self.timeline[-1][0] if self.timeline else 0.0

    def src_at(self, out_t: float) -> float:
        tl = self.timeline
        lo, hi = 0, len(tl) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if tl[mid][0] <= out_t:
                lo = mid
            else:
                hi = mid - 1
        return tl[lo][1]

    def out_at(self, src_t: float) -> float:
        best = 0.0
        for o, s in self.timeline:
            if s > src_t:
                break
            best = o
        return best

    # ── cadre ──
    def _frame_name(self, t: float) -> Optional[str]:
        import bisect
        i = bisect.bisect_right(self._frame_times, t) - 1
        if i < 0:
            i = 0 if self._frame_times else -1
        return self.m["frames"][i][1] if i >= 0 else None

    def frame(self, t: float) -> Image.Image:
        name = self._frame_name(t)
        if name is None:
            return Image.new("RGB", self.size, (30, 30, 46))
        img = self._cache.get(name)
        if img is None:
            img = Image.open(io.BytesIO(self._zip.read(name))).convert("RGB")
            if len(self._cache) > 40:
                self._cache.pop(next(iter(self._cache)))
            self._cache[name] = img
        return img

    def _cursor_at(self, t: float) -> Optional[Tuple[int, int]]:
        pos = None
        for ct, x, y in self.m.get("cursor", []):
            if ct > t:
                break
            pos = (x, y)
        return pos

    def _caption_at(self, t: float) -> List[dict]:
        return [c for c in self.edits.get("captions", []) if c["t0"] <= t <= c["t1"]]

    @staticmethod
    def caption_text(c: dict, lang: str = "ro") -> str:
        txt = c.get("text", "")
        if isinstance(txt, dict):
            return txt.get(lang) or txt.get("ro") or next(iter(txt.values()), "")
        return str(txt)

    def render(self, t: float, lang: str = "ro", cursor: bool = True, clicks: bool = True) -> Image.Image:
        img = self.frame(t).copy()
        draw = ImageDraw.Draw(img, "RGBA")
        # zone ascunse (date personale)
        for b in self.edits.get("blur", []):
            if b["t0"] <= t <= b["t1"]:
                x, y, w, h = [int(v) for v in b["rect"]]
                box = (max(0, x), max(0, y), min(img.width, x + w), min(img.height, y + h))
                if box[2] > box[0] and box[3] > box[1]:
                    region = img.crop(box).filter(ImageFilter.GaussianBlur(12))
                    img.paste(region, box)
        draw = ImageDraw.Draw(img, "RGBA")
        # click-uri: un cerc care se extinde 0.5 s
        if clicks:
            for ct, x, y in self.m.get("clicks", []):
                if 0 <= t - ct <= 0.5:
                    r = int(10 + 40 * (t - ct))
                    a = int(220 * (1 - (t - ct) / 0.5))
                    draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 153, 0, a), width=4)
        # cursor
        if cursor:
            pos = self._cursor_at(t)
            if pos and pos[0] >= 0:
                x, y = pos
                pts = [(x, y), (x, y + 20), (x + 5, y + 15), (x + 9, y + 24), (x + 12, y + 22), (x + 8, y + 14), (x + 15, y + 14)]
                draw.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        # texte (titluri / explicatii)
        caps = self._caption_at(t)
        for i, c in enumerate(caps):
            text = self.caption_text(c, lang)
            if not text:
                continue
            size = max(14, img.height // 32)
            font = _font(size)
            efont = _emoji_font(size)
            lines = _wrap(draw, text, font, int(img.width * 0.8), efont)
            lh = size + 8
            bw = max(_text_len(draw, l, font, efont) for l in lines) + 36
            bh = lh * len(lines) + 20
            pos = c.get("pos", "bottom")
            bx = (img.width - bw) / 2
            by = 24 + i * (bh + 8) if pos == "top" else img.height - bh - 30 - i * (bh + 8)
            draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=10, fill=(20, 20, 30, 215),
                                   outline=(0, 153, 153, 255), width=2)
            for k, line in enumerate(lines):
                _draw_text(draw, (bx + 18, by + 10 + k * lh), line, font, efont, (255, 255, 255, 255))
        return img

    # ── salvare editari / export ──
    def save_edits(self, path: Optional[str] = None) -> str:
        """Scrie manifestul (cu editarile) in acelasi fisier sau intr-o copie."""
        target = path or self.path
        tmp = target + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
            for info in self._zip.infolist():
                if info.filename != "manifest.json":
                    z.writestr(info, self._zip.read(info.filename))
            z.writestr("manifest.json", json.dumps(self.m, ensure_ascii=False))
        self._zip.close()
        os.replace(tmp, target)
        self.path = target
        self._zip = zipfile.ZipFile(target, "r")
        return target

    def export_gif(self, path: str, fps: int = 4, width: int = 960, lang: str = "ro",
                   progress: Optional[Callable[[float], None]] = None) -> str:
        frames, durations = self._sample(fps, width, lang, progress)
        if not frames:
            raise ValueError("Filmul nu are cadre.")
        pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
        pal[0].save(path, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
        return path

    def export_mp4(self, path: str, fps: int = 8, width: int = 1280, lang: str = "ro",
                   progress: Optional[Callable[[float], None]] = None) -> str:
        try:
            import cv2
            import numpy as np
        except ImportError as ex:
            raise RuntimeError("Pentru MP4 lipseste pachetul opencv-python (pip install --user opencv-python). "
                               "Exportul GIF merge fara el.") from ex
        w0, h0 = self.size
        w = min(width, w0) // 2 * 2
        h = int(h0 * w / w0) // 2 * 2
        vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        n = max(1, int(self.out_duration * fps))
        for i in range(n + 1):
            img = self.render(self.src_at(i / fps), lang).resize((w, h), Image.BILINEAR)
            vw.write(cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR))
            if progress and i % 10 == 0:
                progress(i / n)
        vw.release()
        return path

    def _sample(self, fps, width, lang, progress):
        frames, durations = [], []
        w0, h0 = self.size
        w = min(width, w0)
        h = int(h0 * w / w0)
        n = max(1, int(self.out_duration * fps))
        last = None
        for i in range(n + 1):
            img = self.render(self.src_at(i / fps), lang).resize((w, h), Image.BILINEAR)
            if last is not None and ImageChops.difference(img, last).getbbox() is None:
                durations[-1] += int(1000 / fps)   # cadru identic: doar prelungim durata
            else:
                frames.append(img)
                durations.append(int(1000 / fps))
                last = img
            if progress and i % 10 == 0:
                progress(i / n)
        return frames, durations


def _wrap(draw, text: str, font, max_w: int, efont=None) -> List[str]:
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            test = (line + " " + word).strip()
            if _text_len(draw, test, font, efont) <= max_w or not line:
                line = test
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def mp4_available() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


# ─────────────────────────────────────────────────────────────
# 5. Video "construit" din imagini (tutoriale): imagini + texte + cursor animat
# ─────────────────────────────────────────────────────────────
class SlideVideoBuilder:
    """Construieste un .apvid din capturi (ex. ecranele aplicatiei) cu texte in mai multe limbi si
    un cursor care se deplaseaza intre puncte — pentru filmele scurte din 📖 Instructiuni."""

    def __init__(self, title: str, size: Tuple[int, int], fps: int = 8):
        self.m = {"version": 1, "title": title, "created": _dt.datetime.now().isoformat(timespec="seconds"),
                  "size": list(size), "scale": 1.0, "origin": [0, 0], "fps": fps, "duration": 0.0,
                  "frames": [], "cursor": [], "clicks": [], "markers": [],
                  "edits": {"trim": None, "cuts": [], "captions": [], "blur": [], "idle": 0.0}}
        self._images: List[Tuple[str, bytes]] = []
        self.t = 0.0
        self._cur = (size[0] // 2, size[1] // 2)

    def image(self, img: Image.Image, quality: int = 70):
        img = img.convert("RGB")
        if img.size != tuple(self.m["size"]):
            img = img.resize(tuple(self.m["size"]), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=quality, method=5)
        name = f"frames/{len(self._images) + 1:06d}.webp"
        self._images.append((name, buf.getvalue()))
        self.m["frames"].append([round(self.t, 2), name])

    def move(self, x: int, y: int, seconds: float = 0.8, click: bool = False):
        x0, y0 = self._cur
        steps = max(1, int(seconds * self.m["fps"]))
        for i in range(1, steps + 1):
            k = i / steps
            k = k * k * (3 - 2 * k)   # miscare lina
            self.t += seconds / steps
            self.m["cursor"].append([round(self.t, 2), int(x0 + (x - x0) * k), int(y0 + (y - y0) * k)])
        self._cur = (x, y)
        if click:
            self.m["clicks"].append([round(self.t, 2), x, y])
            self.t += 0.3

    def wait(self, seconds: float):
        self.t += seconds

    def caption(self, text: Dict[str, str], seconds: float, pos: str = "bottom"):
        """Text pe ecran (in toate limbile) pentru urmatoarele `seconds` secunde."""
        self.m["edits"]["captions"].append({"t0": round(self.t, 2), "t1": round(self.t + seconds, 2),
                                            "text": text, "pos": pos})

    def marker(self, text: str):
        self.m["markers"].append([round(self.t, 2), text])

    def save(self, path: str) -> str:
        self.m["duration"] = round(self.t + 0.5, 2)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
            for name, data in self._images:
                z.writestr(name, data)
            z.writestr("manifest.json", json.dumps(self.m, ensure_ascii=False))
        return path
