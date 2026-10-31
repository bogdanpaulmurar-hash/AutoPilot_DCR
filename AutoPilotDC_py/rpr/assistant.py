# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.30 — 🤖 Asistent AI (motorul, fara interfata)
#
# Doua lucruri:
#   1. Intrebari despre aplicatie ("cum fac...", "de ce nu merge pasul X") — raspunsul vine din Instructiuni,
#      rutina deschisa si ultimele erori.
#   2. Procedura scrisa -> rutina: promptul din importer.ai_prompt() + procedura; raspunsul trece prin
#      StepImporter, iar daca are erori, AI-ul primeste lista lor si corecteaza (de maxim 2 ori).
#
# Doua moduri de lucru:
#   - fara conexiune: AutoPilot face textul complet (pachetul) si tu il lipesti in AI-ul tau;
#   - cu conexiune: acelasi text se trimite direct la un API: Anthropic (Claude) sau un endpoint compatibil
#     OpenAI (gateway-ul intern al firmei, Azure OpenAI, alte modele). Cheia NU sta in fisierul de setari:
#     keyring (daca e instalat) sau o variabila de mediu.
#
# AI-ul nu ruleaza nimic: o rutina propusa trece prin 📥 Import (verificare, previzualizare), apoi prin
# 🎯 Completeaza obiectele si sistemul de preventie, ca orice rutina.
# ============================================================

from __future__ import annotations

import json
import os
import re
import ssl
import unicodedata
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .importer import ImportResult, StepImporter, ai_prompt, _t


_SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC", "asistent_ai.json")
_DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "instructiuni")
KEYRING_SERVICE = "AutoPilotDC-AI"
DEFAULT_KEY_ENV = "AUTOPILOT_AI_KEY"

PROVIDERS = [("", "Fara conexiune (copiez textul in AI)"),
             ("anthropic", "Anthropic API (Claude)"),
             ("openai", "Compatibil OpenAI (gateway intern, Azure, alte modele)")]
AUTH_HEADERS = [("", "Automat"), ("bearer", "Authorization: Bearer"), ("x-api-key", "x-api-key"),
                ("api-key", "api-key (Azure)")]

DOC_BUDGET = 18000       # caractere din Instructiuni trimise la o intrebare (modelele mici au nevoie de putin)
ROUTINE_BUDGET = 6000    # rutina deschisa, ca schita
MAX_REPAIRS = 2          # de cate ori primeste AI-ul erorile importului inapoi


class AiError(Exception):
    """Eroare de conexiune / raspuns, cu mesaj pentru om."""


# ─────────────────────────────────────────────────────────────
# Setarile conexiunii
# ─────────────────────────────────────────────────────────────
@dataclass
class AiSettings:
    provider: str = ""            # "" = fara conexiune; "anthropic"; "openai"
    url: str = ""                 # adresa API (gol = cea publica a furnizorului)
    model: str = ""
    auth_header: str = ""         # "" = automat dupa furnizor
    key_env: str = DEFAULT_KEY_ENV
    ca_file: str = ""             # certificatul firmei (proxy cu inspectie SSL); gol = cele din Windows / Python
    max_tokens: int = 4000
    timeout: int = 120
    send_routine: bool = True     # rutina deschisa intra in intrebare
    send_errors: bool = True      # ultimele erori din rulare intra in intrebare

    @property
    def connected(self) -> bool:
        return bool(self.provider and self.model)

    def label(self) -> str:
        if not self.connected:
            return _t("Fara conexiune: copiezi textul in AI-ul tau")
        return f"{dict(PROVIDERS).get(self.provider, self.provider).split(' (')[0]} · {self.model}"

    @staticmethod
    def load(path: Optional[str] = None) -> "AiSettings":
        try:
            with open(path or _SETTINGS, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return AiSettings()
        s = AiSettings()
        for k, v in (data or {}).items():
            if hasattr(s, k) and k != "key" and isinstance(v, type(getattr(s, k))):
                setattr(s, k, v)
        return s

    def save(self, path: Optional[str] = None) -> None:
        path = path or _SETTINGS
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=1)


# ── cheia: keyring sau variabila de mediu (niciodata in fisier) ──
def _keyring():
    try:
        import keyring  # type: ignore
        return keyring
    except Exception:
        return None


def get_key(s: AiSettings) -> str:
    env = os.environ.get(s.key_env or DEFAULT_KEY_ENV, "").strip()
    if env:
        return env
    kr = _keyring()
    if kr is not None:
        try:
            return (kr.get_password(KEYRING_SERVICE, s.provider or "default") or "").strip()
        except Exception:
            return ""
    return ""


def set_key(s: AiSettings, key: str) -> bool:
    """Salveaza cheia in keyring. False = keyring lipseste (atunci: variabila de mediu)."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        if key:
            kr.set_password(KEYRING_SERVICE, s.provider or "default", key)
        else:
            kr.delete_password(KEYRING_SERVICE, s.provider or "default")
        return True
    except Exception:
        return False


def key_source(s: AiSettings) -> str:
    if os.environ.get(s.key_env or DEFAULT_KEY_ENV, "").strip():
        return "env"
    return "keyring" if get_key(s) else ""


# ─────────────────────────────────────────────────────────────
# Clientul HTTP (doar biblioteca standard: nimic de instalat)
# ─────────────────────────────────────────────────────────────
Message = Dict[str, str]   # {"role": "user" | "assistant", "content": "..."}


def endpoint(s: AiSettings) -> str:
    url = (s.url or "").strip().rstrip("/")
    if s.provider == "anthropic":
        url = url or "https://api.anthropic.com"
        if url.endswith("/messages"):
            return url
        return url + ("/messages" if url.endswith("/v1") else "/v1/messages")
    url = url or "https://api.openai.com/v1"
    if "/chat/completions" in url:
        return url
    return url + "/chat/completions"


def _headers(s: AiSettings, key: str) -> Dict[str, str]:
    h = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "AutoPilotDC"}
    auth = s.auth_header or ("x-api-key" if s.provider == "anthropic" else "bearer")
    if key:
        if auth == "bearer":
            h["Authorization"] = "Bearer " + key
        else:
            h[auth] = key
    if s.provider == "anthropic":
        h["anthropic-version"] = "2023-06-01"
    return h


def build_request(s: AiSettings, system: str, messages: Sequence[Message], key: str) -> Tuple[str, Dict, bytes]:
    if s.provider == "anthropic":
        body = {"model": s.model, "max_tokens": s.max_tokens, "system": system, "messages": list(messages)}
    else:
        body = {"model": s.model, "max_tokens": s.max_tokens,
                "messages": [{"role": "system", "content": system}] + list(messages)}
    return endpoint(s), _headers(s, key), json.dumps(body, ensure_ascii=False).encode("utf-8")


def parse_response(provider: str, data: dict) -> str:
    if provider == "anthropic":
        parts = [c.get("text", "") for c in data.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
        text = "".join(parts)
    else:
        ch = (data.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content", ch.get("text", ""))
        if isinstance(content, list):   # unele gateway-uri intorc bucati
            content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
        text = content or ""
    if not text.strip():
        raise AiError(_t("AI-ul a trimis un raspuns gol."))
    return text


Transport = Callable[[str, Dict[str, str], bytes, int, Optional[ssl.SSLContext]], dict]


def _http_post(url: str, headers: Dict[str, str], body: bytes, timeout: int, ctx: Optional[ssl.SSLContext]) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:   # proxy-ul: din variabilele de mediu
            return json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as ex:
        detail = ""
        try:
            detail = ex.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        hint = {401: _t("cheia lipseste sau e gresita"), 403: _t("acces refuzat (cheia nu are drept la model)"),
                404: _t("adresa sau modelul nu exista"), 429: _t("prea multe cereri: incearca peste un minut")}.get(
            ex.code, "")
        raise AiError(f"HTTP {ex.code}" + (f": {hint}" if hint else "") + (f"\n{detail}" if detail else ""))
    except urllib.error.URLError as ex:
        reason = str(getattr(ex, "reason", ex))
        if "CERTIFICATE" in reason.upper():
            reason += "\n" + _t("Daca firma are proxy cu certificat propriu: alege fisierul certificatului in ⚙ Conexiune.")
        raise AiError(_t("Nu ma pot conecta la {0}: {1}").format(url, reason))
    except (OSError, ValueError) as ex:
        raise AiError(_t("Nu ma pot conecta la {0}: {1}").format(url, ex))


class AiClient:
    def __init__(self, settings: AiSettings, key: Optional[str] = None, transport: Optional[Transport] = None):
        self.s = settings
        self.key = get_key(settings) if key is None else key
        self.transport = transport or _http_post

    def complete(self, system: str, messages: Sequence[Message]) -> str:
        if not self.s.connected:
            raise AiError(_t("Conexiunea nu e configurata (⚙ Conexiune: furnizor si model)."))
        url, headers, body = build_request(self.s, system, messages, self.key)
        ctx = None
        if url.startswith("https"):
            ctx = ssl.create_default_context(cafile=self.s.ca_file or None) if self.s.ca_file else None
        data = self.transport(url, headers, body, int(self.s.timeout or 120), ctx)
        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            raise AiError(str(err.get("message") if isinstance(err, dict) else err))
        return parse_response(self.s.provider, data)

    def test(self) -> str:
        return self.complete(_t("Raspunde scurt."), [{"role": "user", "content": "OK?"}])


# ─────────────────────────────────────────────────────────────
# Contextul: Instructiunile, rutina deschisa, erorile
# ─────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return s


_STOP = set("si sau de la in pe cu un o ca ce cum nu sa se din care este e am ai the a an and or to of in on for how "
            "is it do i my what why und oder der die das ein eine wie ich nicht mit zu".split())


def _words(s: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]{3,}", _norm(s)) if w not in _STOP]


def load_chapters(lang: str = "ro") -> List[Tuple[str, str]]:
    for code in (lang, "ro"):
        try:
            with open(os.path.join(_DOCS, code + ".md"), encoding="utf-8") as f:
                text = f.read()
            break
        except OSError:
            continue
    else:
        return []
    out: List[Tuple[str, str]] = []
    title, cur = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                out.append((title, "\n".join(cur).strip()))
            title, cur = line[3:].strip(), []
        elif title is not None:
            cur.append(line)
    if title is not None:
        out.append((title, "\n".join(cur).strip()))
    return out


def pick_chapters(question: str, chapters: List[Tuple[str, str]], budget: int = DOC_BUDGET,
                  always: Sequence[str] = ()) -> List[Tuple[str, str]]:
    """Capitolele cele mai potrivite cu intrebarea, pana la `budget` caractere (in ordinea din document)."""
    q = _words(question)
    if not q:
        q = []
    scores = []
    for i, (title, body) in enumerate(chapters):
        tw, bw = _words(title), _words(body)
        bag: Dict[str, int] = {}
        for w in bw:
            bag[w] = bag.get(w, 0) + 1
        score = 0.0
        for w in set(q):
            score += 4 * tw.count(w) + min(bag.get(w, 0), 6)
            # cuvinte inrudite: "rutina" / "rutinei", "excel" / "excelul"
            if len(w) >= 5:
                score += 0.5 * sum(1 for t in tw if t != w and t[:5] == w[:5])
        if any(_norm(a) in _norm(title) for a in always):
            score += 1000
        scores.append((score, i))
    chosen, used = set(), 0
    for score, i in sorted(scores, key=lambda x: -x[0]):
        if score <= 0:
            break
        size = len(chapters[i][0]) + len(chapters[i][1]) + 8
        if used + size > budget:
            continue
        chosen.add(i)
        used += size
    if not chosen and chapters:   # nimic potrivit: cuprinsul ajuta modelul sa spuna unde sa te uiti
        return []
    return [chapters[i] for i in sorted(chosen)]


def routine_outline(routine, budget: int = ROUTINE_BUDGET) -> str:
    """Rutina ca schita cu indentare (titlurile pasilor, ramurile, variabilele)."""
    if routine is None:
        return ""
    lines = [f"{_t('Rutina')}: {routine.name}"]
    vars_ = getattr(routine, "variables", None) or []
    names = []
    for v in vars_:
        n = getattr(v, "name", None) or (v.get("name") if isinstance(v, dict) else str(v))
        if n:
            names.append(str(n))
    if names:
        lines.append(_t("Variabile") + ": " + ", ".join(names[:40]))
    n = [0]

    def add(node, depth):
        n[0] += 1
        off = "" if getattr(node, "enabled", True) else "  [" + _t("dezactivat") + "]"
        note = getattr(node, "comment", "") or ""
        lines.append(f"{'  ' * depth}{n[0]}. {node.title}{off}" + (f"   # {note[:80]}" if note else ""))
        br = node.branches()
        for name, lst in br:
            if len(br) > 1:
                lines.append(f"{'  ' * (depth + 1)}▸ {_t(name)}")
            for ch in lst:
                add(ch, depth + (2 if len(br) > 1 else 1))
    for node in routine.steps:
        add(node, 1)
    text = "\n".join(lines)
    if len(text) > budget:
        text = text[:budget] + "\n  … (" + _t("rutina continua") + ")"
    return text


def errors_text(entries, limit: int = 8) -> str:
    """Ultimele erori / avertismente din rulare (cele mai noi la final)."""
    picked = [e for e in entries or [] if str(getattr(e, "level", "")) in ("Error", "Warning")][-limit:]
    out = []
    for e in picked:
        row = f" [{_t('rand')} {e.excel_row}]" if getattr(e, "excel_row", 0) else ""
        out.append(f"- {e.level}{row} {e.node_title}: {str(e.message).strip()[:400]}")
    return "\n".join(out)


_ASK_SYSTEM = [
    "Esti asistentul aplicatiei AutoPilot DC, un tool RPA care automatizeaza browserul, SAP GUI si aplicatii "
    "Windows prin rutine de pasi (Studio RPR), cu date din Excel. Raspunzi doar despre AutoPilot DC si rutinele lui.",
    "- Raspunde in limba intrebarii, scurt, cu pasi numerotati pe care omul ii face in aplicatie (numele butoanelor "
    "exact ca in Instructiuni).",
    "- Foloseste doar Instructiunile si datele de mai jos. Daca nu scrie acolo, spune ca nu stii sigur si ce ar "
    "trebui verificat; nu inventa butoane sau functii.",
    "- La o eroare: spune cauza probabila, apoi ce schimba omul in pas sau in obiect (🎯 Remarcheaza, ⏱ Asteapta, "
    "DACA APARE etc.).",
    "- Daca raspunsul e o rutina sau o bucata de rutina, pune-o intr-un bloc ```text in formatul Pasi AutoPilot "
    "(omul o lipeste in 📥 Import AI).",
    "- Nu cere si nu repeta parole, chei sau date personale.",
]


def ask_system(lang: str = "ro") -> str:
    return "\n".join(_t(x) for x in _ASK_SYSTEM)


def objects_text(outline: str, repo, limit: int = 40) -> str:
    """Obiectele din bibliotecă folosite de rutina (din schita: [Nume]), cu locatoarele lor."""
    if repo is None or not outline:
        return ""
    out, seen = [], set()
    for name in re.findall(r"\[([^\[\]\n]{1,80})\]", outline):
        if name in seen or len(out) >= limit:
            continue
        seen.add(name)
        o = repo.find(name) if hasattr(repo, "find") else None
        if o is None:
            continue
        locs = "; ".join(f"{getattr(l.kind, 'value', l.kind)}={str(l.value)[:80]}" for l in (o.active_locators or [])[:3])
        out.append(f"- [{o.name}] {o.object_type or o.technology}" + (f": {locs}" if locs else ""))
    return "\n".join(out)


def ask_context(question: str, lang: str = "ro", routine=None, log_entries=None, settings: Optional[AiSettings] = None,
                chapters: Optional[List[Tuple[str, str]]] = None, repo=None) -> str:
    """Mesajul utilizatorului pentru o intrebare: Instructiunile potrivite + rutina + erori + intrebarea."""
    s = settings or AiSettings()
    chapters = load_chapters(lang) if chapters is None else chapters
    err = errors_text(log_entries) if s.send_errors else ""
    always = ("19.",) if err else ()   # capitolul 19: Probleme frecvente (acelasi numar in RO / EN / DE)
    parts: List[str] = []
    picked = pick_chapters(question + "\n" + err, chapters, always=always)
    if chapters:
        parts.append("## " + _t("CUPRINSUL INSTRUCTIUNILOR") + "\n" + "\n".join("- " + t for t, _ in chapters))
    if picked:
        parts.append("## " + _t("INSTRUCTIUNI (capitolele potrivite)") + "\n\n" +
                     "\n\n".join(f"### {t}\n{b}" for t, b in picked))
    if s.send_routine and routine is not None and getattr(routine, "steps", None):
        outline = routine_outline(routine)
        parts.append("## " + _t("RUTINA DESCHISA") + "\n" + outline)
        objs = objects_text(outline, repo)
        if objs:
            parts.append("## " + _t("OBIECTELE RUTINEI (locatoare)") + "\n" + objs)
    if err:
        parts.append("## " + _t("ULTIMELE ERORI DIN RULARE") + "\n" + err)
    parts.append("## " + _t("INTREBAREA") + "\n" + question.strip())
    return "\n\n".join(parts)


def ask_copy_text(question: str, lang: str = "ro", routine=None, log_entries=None,
                  settings: Optional[AiSettings] = None, repo=None) -> str:
    """Tot pachetul intr-un singur text, de lipit in orice chat AI (modul fara conexiune)."""
    return ask_system(lang) + "\n\n" + ask_context(question, lang, routine, log_entries, settings, repo=repo)


def ask(client: AiClient, question: str, lang: str = "ro", routine=None, log_entries=None,
        history: Optional[List[Message]] = None, repo=None) -> str:
    """O intrebare; `history` = schimburile anterioare (doar intrebarea si raspunsul, fara context)."""
    msgs = list(history or []) + [{"role": "user", "content": ask_context(question, lang, routine, log_entries,
                                                                           client.s, repo=repo)}]
    return client.complete(ask_system(lang), msgs)


# ─────────────────────────────────────────────────────────────
# Procedura -> rutina (cu corectare automata)
# ─────────────────────────────────────────────────────────────
def routine_copy_text(procedure: str, lang: str = "ro", objects=None) -> str:
    """Promptul de import + procedura, intr-un singur text (modul fara conexiune)."""
    return ai_prompt(lang, objects) + "\n" + procedure.strip() + "\n"


def repair_request(result: ImportResult, limit: int = 15) -> str:
    lines = [_t("Importul in AutoPilot a gasit erori in rutina ta:")]
    for i in result.errors[:limit]:
        where = _t("randul {0}").format(i.line) + (f" `{i.text.strip()[:120]}`" if i.text.strip() else "") \
            if i.line else _t("tot textul")
        lines.append(f"- {where}: {i.message}")
    lines += ["", _t("Corecteaza-le si trimite din nou rutina COMPLETA, intr-un singur bloc ```text, fara alte "
                     "explicatii. Pastreaza regulile si comenzile din primul mesaj.")]
    return "\n".join(lines)


@dataclass
class RoutineDraft:
    text: str                                  # ultimul raspuns al AI-ului (de pus in 📥 Import)
    result: ImportResult
    attempts: int = 1
    log: List[str] = field(default_factory=list)


def make_routine(client: AiClient, procedure: str, repo, lang: str = "ro", max_repairs: int = MAX_REPAIRS,
                 progress: Optional[Callable[[str], None]] = None) -> RoutineDraft:
    """Trimite procedura, citeste rutina cu StepImporter si, la erori, cere corectura (de max_repairs ori)."""
    say = progress or (lambda _m: None)
    objects = list(getattr(repo, "objects", []) or [])
    system = ai_prompt(lang, objects)
    msgs: List[Message] = [{"role": "user", "content": procedure.strip()}]
    say(_t("Trimit procedura la AI…"))
    text = client.complete(system, msgs)
    res = StepImporter(repo).parse(text)
    draft = RoutineDraft(text, res, 1, [_t("Incercarea 1: {0} pasi, {1} erori").format(res.step_count(),
                                                                                        len(res.errors))])
    while res.errors and draft.attempts <= max_repairs:
        say(_t("Rutina are {0} erori: AI-ul o corecteaza (incercarea {1})…").format(len(res.errors), draft.attempts + 1))
        msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": repair_request(res)}]
        text = client.complete(system, msgs)
        res = StepImporter(repo).parse(text)
        draft.attempts += 1
        draft.text, draft.result = text, res
        draft.log.append(_t("Incercarea {0}: {1} pasi, {2} erori").format(draft.attempts, res.step_count(),
                                                                          len(res.errors)))
    return draft


# ─────────────────────────────────────────────────────────────
# 🔧 Repara rutina: rutina existenta + erorile + ce s-a schimbat -> rutina corectata (tab nou)
# ─────────────────────────────────────────────────────────────
_REPAIR_RULES = [
    "REPARAREA UNEI RUTINE EXISTENTE:",
    "- Primesti rutina actuala in formatul de mai sus, ultimele erori din rulare si ce s-a schimbat in aplicatie.",
    "- Intoarce rutina COMPLETA corectata, intr-un singur bloc ```text. Schimba doar ce trebuie pentru erori si "
    "pentru schimbarile descrise; restul randurilor raman EXACT la fel (pastreaza-le setarile).",
    "- Randurile PASTREAZA #n sunt pasi pe care textul nu ii poate arata: lasa-le neschimbate, in acelasi loc, "
    "daca nu e nevoie clar sa dispara.",
    "- Obiectele [Nume] exista in biblioteca. Daca un obiect s-a schimbat pe ecran, foloseste un obiect nou "
    "(buton \"Text nou\", css \"...\") si pune # TODO deasupra; nu redenumi obiectele existente.",
    "- Pentru un mesaj care apare doar uneori foloseste DACA APARE ... SFARSIT; pentru un ecran lent, "
    "ASTEAPTA <obiect> MAX <secunde> inainte de pas.",
    "- Dupa bloc, o lista scurta SCHIMBARI: ce ai modificat si de ce.",
]


def repair_system(lang: str = "ro", objects=None) -> str:
    return ai_prompt(lang, objects, repair=True).rsplit("\n", 2)[0] + "\n\n" + "\n".join(_t(x) for x in _REPAIR_RULES)


def repair_message(steps_text: str, note: str, log_entries=None) -> str:
    parts = ["## " + _t("RUTINA ACTUALA") + "\n```text\n" + steps_text.rstrip() + "\n```"]
    err = errors_text(log_entries)
    if err:
        parts.append("## " + _t("ULTIMELE ERORI DIN RULARE") + "\n" + err)
    parts.append("## " + _t("CE S-A SCHIMBAT / CE TREBUIE REPARAT") + "\n" +
                 (note.strip() or _t("(nimic scris: repara erorile de mai sus)")))
    return "\n\n".join(parts)


@dataclass
class RepairJob:
    """Tot ce trebuie ca raspunsul AI-ului sa devina rutina: textul trimis, pasii PASTREAZA, originalul."""
    original: object
    writer: object
    steps_text: str
    lang: str = "ro"

    def importer(self, repo) -> StepImporter:
        return StepImporter(repo, keep=self.writer.keep)

    def finish(self, result: ImportResult) -> int:
        """Rutina importata primeste setarile originalului; randurile neschimbate isi recapata setarile."""
        from .steps_text import restore_settings
        r, o = result.routine, self.original
        n = restore_settings(r, self.writer, self.lang)
        r.settings = type(o.settings).from_dict(o.settings.to_dict())
        r.repository_path = o.repository_path
        r.extra = dict(o.extra)
        from .steps_text import MASK
        merged = {**o.variables, **r.variables}
        for k, v in o.variables.items():   # parolele au plecat ca *** : revin valorile originale
            if merged.get(k) == MASK:
                merged[k] = v
        r.variables = merged
        r.name = _t("{0} (reparata)").format(o.name)
        r.description = o.description
        return n


def prepare_repair(routine, lang: str = "ro") -> RepairJob:
    from .steps_text import routine_to_steps
    text, w = routine_to_steps(routine, lang)
    return RepairJob(routine, w, text, lang)


def repair_copy_text(job: RepairJob, note: str, log_entries=None, objects=None) -> str:
    return repair_system(job.lang, objects) + "\n\n" + repair_message(job.steps_text, note, log_entries)


def repair_routine(client: AiClient, job: RepairJob, note: str, repo, log_entries=None,
                   max_repairs: int = MAX_REPAIRS, progress: Optional[Callable[[str], None]] = None) -> RoutineDraft:
    say = progress or (lambda _m: None)
    system = repair_system(job.lang, list(getattr(repo, "objects", []) or []))
    msgs: List[Message] = [{"role": "user", "content": repair_message(job.steps_text, note, log_entries)}]
    say(_t("Trimit rutina la AI…"))
    text = client.complete(system, msgs)
    res = job.importer(repo).parse(text)
    draft = RoutineDraft(text, res, 1, [_t("Incercarea 1: {0} pasi, {1} erori").format(res.step_count(),
                                                                                        len(res.errors))])
    while res.errors and draft.attempts <= max_repairs:
        say(_t("Rutina are {0} erori: AI-ul o corecteaza (incercarea {1})…").format(len(res.errors), draft.attempts + 1))
        msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": repair_request(res)}]
        text = client.complete(system, msgs)
        res = job.importer(repo).parse(text)
        draft.attempts += 1
        draft.text, draft.result = text, res
        draft.log.append(_t("Incercarea {0}: {1} pasi, {2} erori").format(draft.attempts, res.step_count(),
                                                                          len(res.errors)))
    return draft


def extract_text_block(answer: str) -> str:
    """Blocurile ```text din raspuns (lipite), pentru 📥 Import; "" daca nu are."""
    blocks = re.findall(r"```(?:text|txt)?[ \t]*\n(.*?)```", answer or "", flags=re.S)
    return "\n".join(b.strip("\n") for b in blocks if b.strip())


# ─────────────────────────────────────────────────────────────
# Procedura din fisier (.txt / .md / .docx), fara pachete in plus
# ─────────────────────────────────────────────────────────────
def read_procedure(path: str) -> str:
    if path.lower().endswith(".docx"):
        return docx_text(path)
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def docx_text(path: str) -> str:
    """Textul unui document Word: paragrafele (titluri, liste) si tabelele, rand cu rand."""
    import xml.etree.ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as ex:
        raise AiError(_t("Nu pot citi documentul Word: {0}").format(ex))
    root = ET.fromstring(xml)
    out: List[str] = []

    def para(p) -> str:
        bits = []
        for el in p.iter():
            if el.tag == ns + "t":
                bits.append(el.text or "")
            elif el.tag == ns + "tab":
                bits.append("\t")
            elif el.tag in (ns + "br", ns + "cr"):
                bits.append("\n")
        txt = "".join(bits).strip()
        if txt and p.find(f"{ns}pPr/{ns}numPr") is not None:
            txt = "- " + txt
        return txt

    body = root.find(ns + "body")
    for el in (body if body is not None else []):
        if el.tag == ns + "p":
            t = para(el)
            if t:
                out.append(t)
        elif el.tag == ns + "tbl":
            for tr_ in el.iter(ns + "tr"):
                cells = [" ".join(para(p) for p in tc.iter(ns + "p")).strip() for tc in tr_.iter(ns + "tc")]
                if any(cells):
                    out.append(" | ".join(cells))
    return "\n".join(out)
