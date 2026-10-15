// ============================================================
// AutoPilot DC v4.1
// SafetyGuard.cs — Sistemul de preventie
//
// Inainte de fiecare pas verifica daca ecranul arata ca la inregistrare.
// Daca ceva difera, rutina se opreste (pauza) si te intreaba ce faci.
//
//  1. Mouse miscat de altcineva intre pasi (ai pus mana pe mouse).
//  2. Ferestre noi de eroare / avertisment (ex: "Eroare", "Warning", dialoguri Windows).
//  3. Aplicatia nu raspunde.
//  4. Click-ul ar ajunge in alta aplicatie decat la inregistrare.
//  5. Zona din jurul click-ului arata diferit (alt continut, popup, notificare peste ea).
//  6. Tastele ar ajunge in alta aplicatie decat la inregistrare.
//
// Pasii inregistrati inainte de v4.1 nu au context: se verifica doar 1-3.
// ============================================================

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Safety;

public enum GuardSensitivity { Relaxed, Normal, Strict }

/// <summary>Ce a gasit sistemul de preventie.</summary>
public sealed record GuardAlert(string Title, string Details, string IgnoreKey, bool CanIgnoreStep = true);

/// <summary>Raspunsul utilizatorului.</summary>
public enum GuardDecision
{
    /// <summary>Continua (am rezolvat / e in regula).</summary>
    Continue,
    /// <summary>Continua si nu mai verifica acest pas (se salveaza in rutina).</summary>
    IgnoreStep,
    /// <summary>Reincearca pasul (doar dupa o eroare de executie).</summary>
    Retry,
    /// <summary>Sari peste pas.</summary>
    SkipStep,
    /// <summary>Opreste rutina.</summary>
    Stop,
}

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class SafetyGuard
{
    public bool Enabled { get; set; } = true;
    public GuardSensitivity Sensitivity { get; set; } = GuardSensitivity.Normal;

    private readonly WindowWatcher _windows = new();
    private (int X, int Y)? _cursorAfterLastStep;

    public static GuardSensitivity ParseSensitivity(string? s) => (s ?? "").ToLowerInvariant() switch
    {
        "relaxed" or "relaxat" => GuardSensitivity.Relaxed,
        "strict" => GuardSensitivity.Strict,
        _ => GuardSensitivity.Normal,
    };

    /// <summary>Cat de diferita poate fi zona click-ului (procente) inainte sa intrebam.</summary>
    public double ScreenThreshold => Sensitivity switch
    {
        GuardSensitivity.Relaxed => 35,
        GuardSensitivity.Strict => 12,
        _ => 22,
    };

    /// <summary>Apelat la inceputul rularii (dupa numaratoarea inversa).</summary>
    public void BeginRun()
    {
        _windows.Reset();
        _cursorAfterLastStep = ScreenProbe.CursorPosition();
    }

    /// <summary>Dupa ce utilizatorul a raspuns: ce e acum pe ecran devine "normal".</summary>
    public void Acknowledge()
    {
        _windows.AcceptCurrent();
        _cursorAfterLastStep = ScreenProbe.CursorPosition();
    }

    /// <summary>Dupa fiecare pas executat: tinem minte unde a ramas mouse-ul.</summary>
    public void AfterStep() => _cursorAfterLastStep = ScreenProbe.CursorPosition();

    /// <summary>
    /// Verifica inainte de pas. Poate muta mouse-ul pe tinta (ca la inregistrare)
    /// pentru a compara zona. Returneaza null daca totul e in regula.
    /// </summary>
    public GuardAlert? CheckBeforeStep(StepModel step, IReadOnlyList<StepModel> upcoming)
    {
        if (!Enabled) return null;

        // 1. Mouse miscat de utilizator intre pasi
        if (_cursorAfterLastStep is { } last)
        {
            var now = ScreenProbe.CursorPosition();
            int dist = Math.Abs(now.X - last.X) + Math.Abs(now.Y - last.Y);
            if (dist > 40)
            {
                _cursorAfterLastStep = now;
                return new GuardAlert(
                    "Mouse-ul a fost miscat in timpul rularii",
                    $"Mouse-ul era la ({last.X}, {last.Y}) si acum e la ({now.X}, {now.Y}).\n" +
                    "Daca lucrezi in paralel, rutina poate da click unde nu trebuie.\n" +
                    "Ia mana de pe mouse si apasa Continua cand esti gata.",
                    "mouse", CanIgnoreStep: false);
            }
        }

        // 2. Ferestre noi de eroare (cele asteptate de pasii urmatori nu conteaza)
        var expectedTitles = upcoming.Take(4)
            .Select(s => s.WindowTitle)
            .Where(t => !string.IsNullOrWhiteSpace(t))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
        bool hasContext = upcoming.Take(4).Any(s => !string.IsNullOrEmpty(s.WindowProcess));
        var alert = _windows.CheckNewWindows(expectedTitles, reportAllDialogs: hasContext);
        if (alert != null) return alert;

        // 3. Aplicatia activa nu raspunde
        var fg = ScreenProbe.Foreground();
        if (!ScreenProbe.IsOwn(fg) && ScreenProbe.IsHung(fg.Handle))
            return new GuardAlert("Aplicatia nu raspunde",
                $"Fereastra {fg} nu raspunde (Windows o arata ca \"Not Responding\").\n" +
                "Asteapta sa-si revina, apoi apasa Continua.", "hung:" + fg.Process, CanIgnoreStep: false);

        if (step.GuardIgnore) return null;

        // 4-5. Pasi cu click: aplicatia de sub mouse + amprenta zonei
        if (step.StepType is "CLICK" or "DBLCLICK" or "RIGHTCLICK")
            return CheckClick(step);

        // 6. Taste: ajung in aceeasi aplicatie ca la inregistrare?
        if (step.StepType is "TYPE" or "KEY" && !string.IsNullOrEmpty(step.WindowProcess))
        {
            if (!ScreenProbe.IsOwn(fg) && fg.Process.Length > 0 &&
                !string.Equals(fg.Process, step.WindowProcess, StringComparison.OrdinalIgnoreCase))
            {
                return new GuardAlert("Tastele ar ajunge in alta aplicatie",
                    $"La inregistrare scriai in: {Describe(step.WindowTitle, step.WindowProcess)}\n" +
                    $"Acum fereastra activa este: {fg}\n" +
                    "Activeaza fereastra corecta, apoi apasa Continua.", "keys:" + step.StepId);
            }
        }
        return null;
    }

    private GuardAlert? CheckClick(StepModel step)
    {
        if (string.IsNullOrEmpty(step.WindowProcess) && string.IsNullOrEmpty(step.ScreenSignature))
            return null; // pas vechi, fara context

        // Mouse-ul pe tinta (hover ca la inregistrare), apoi comparam
        ScreenProbe.MoveCursor(step.X, step.Y);
        Thread.Sleep(150);
        _cursorAfterLastStep = (step.X, step.Y);

        var here = ScreenProbe.WindowAt(step.X, step.Y);
        bool recordedOwn = step.WindowProcess.Equals("autopilotdc.ui.exe", StringComparison.OrdinalIgnoreCase);
        if (!ScreenProbe.IsOwn(here) && !recordedOwn && !string.IsNullOrEmpty(step.WindowProcess) && here.Process.Length > 0)
        {
            if (!string.Equals(here.Process, step.WindowProcess, StringComparison.OrdinalIgnoreCase))
                return new GuardAlert("Click-ul ar ajunge in alta aplicatie",
                    $"La inregistrare, la ({step.X}, {step.Y}) era: {Describe(step.WindowTitle, step.WindowProcess)}\n" +
                    $"Acum acolo este: {here}\n" +
                    "Aduce fereastra corecta in fata (sau inchide ce o acopera), apoi apasa Continua.",
                    "click:" + step.StepId);

            if (Sensitivity == GuardSensitivity.Strict && !SimilarTitles(step.WindowTitle, here.Title))
                return new GuardAlert("Alta fereastra decat la inregistrare",
                    $"La inregistrare: \"{step.WindowTitle}\"\nAcum: \"{here.Title}\"", "title:" + step.StepId);
        }

        if (!string.IsNullOrEmpty(step.ScreenSignature) && !ScreenProbe.IsOwn(here))
        {
            var diff = ScreenProbe.CompareSignatures(step.ScreenSignature, ScreenProbe.CaptureSignature(step.X, step.Y));
            if (diff > ScreenThreshold)
                return new GuardAlert("Ecranul arata diferit fata de inregistrare",
                    $"Zona din jurul click-ului ({step.X}, {step.Y}) difera cu {diff:0}% " +
                    $"(limita: {ScreenThreshold:0}%).\n" +
                    "Posibil: alt ecran deschis, un popup / o notificare peste buton, date diferite, fereastra mutata.\n" +
                    "Verifica ecranul. Daca e in regula, apasa Continua.",
                    "screen:" + step.StepId);
        }
        return null;
    }

    /// <summary>
    /// La inregistrare: salveaza in pas fereastra si amprenta zonei (pentru verificarea de la rulare).
    /// Se apeleaza imediat la click (din hook), inainte ca aplicatia sa reactioneze.
    /// </summary>
    public static void RecordContext(StepModel step)
    {
        try
        {
            if (step.StepType is "CLICK" or "DBLCLICK" or "RIGHTCLICK")
            {
                var w = ScreenProbe.WindowAt(step.X, step.Y);
                step.WindowTitle = w.Title;
                step.WindowProcess = w.Process;
                step.ScreenSignature = ScreenProbe.CaptureSignature(step.X, step.Y) ?? "";
            }
            else if (step.StepType is "TYPE" or "KEY" or "SCROLL")
            {
                var w = step.StepType == "SCROLL" ? ScreenProbe.WindowAt(step.X, step.Y) : ScreenProbe.Foreground();
                step.WindowTitle = w.Title;
                step.WindowProcess = w.Process;
            }
        }
        catch { /* contextul e optional */ }
    }

    private static string Describe(string title, string process) =>
        string.IsNullOrEmpty(title) ? $"[{process}]" : $"\"{title}\" ({process})";

    /// <summary>Titluri "la fel" daca, fara cifre, unul il contine pe celalalt sau au un cuvant lung comun.</summary>
    internal static bool SimilarTitles(string a, string b)
    {
        static string Norm(string s) => Regex.Replace(s.ToLowerInvariant(), @"[\d\W_]+", " ").Trim();
        var x = Norm(a);
        var y = Norm(b);
        if (x.Length == 0 || y.Length == 0) return true;
        if (x.Contains(y) || y.Contains(x)) return true;
        var wx = x.Split(' ').Where(w => w.Length >= 4).ToHashSet();
        return y.Split(' ').Any(w => w.Length >= 4 && wx.Contains(w));
    }
}

/// <summary>
/// Urmareste ferestrele noi aparute in timpul rularii si le raporteaza pe cele care arata a eroare.
/// Folosit si de Studio RPR.
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class WindowWatcher
{
    private readonly HashSet<IntPtr> _known = new();
    private readonly HashSet<string> _ignoredTitles = new(StringComparer.OrdinalIgnoreCase);

    public void Reset()
    {
        _known.Clear();
        _ignoredTitles.Clear();
        AcceptCurrent();
    }

    /// <summary>Ferestrele de acum nu mai sunt "noi".</summary>
    public void AcceptCurrent()
    {
        foreach (var w in ScreenProbe.TopLevelWindows()) _known.Add(w.Handle);
    }

    public void IgnoreTitle(string title) => _ignoredTitles.Add(title);

    /// <summary>
    /// Cauta ferestre noi care arata a eroare. <paramref name="reportAllDialogs"/> = si dialogurile
    /// Windows fara cuvinte de eroare (cand stim din inregistrare ce ferestre trebuie sa apara).
    /// </summary>
    public GuardAlert? CheckNewWindows(ISet<string>? expectedTitles = null, bool reportAllDialogs = false)
    {
        foreach (var w in ScreenProbe.TopLevelWindows())
        {
            if (_known.Contains(w.Handle)) continue;
            _known.Add(w.Handle);
            if (ScreenProbe.IsOwn(w)) continue;
            if (_ignoredTitles.Contains(w.Title)) continue;
            if (expectedTitles != null && expectedTitles.Contains(w.Title)) continue;

            string text = w.IsDialog ? ScreenProbe.DialogText(w.Handle) : "";
            bool error = ScreenProbe.LooksLikeError(w.Title) || ScreenProbe.LooksLikeError(text);
            if (!error && !(reportAllDialogs && w.IsDialog)) continue;

            return new GuardAlert(
                error ? "A aparut o fereastra de eroare" : "A aparut o fereastra neasteptata",
                $"Fereastra: {w}" + (text.Length > 0 ? $"\n\nMesaj:\n{text}" : "") +
                "\n\nRezolv-o (citeste mesajul, inchide fereastra daca e cazul), apoi apasa Continua.",
                "window:" + w.Title, CanIgnoreStep: false);
        }
        return null;
    }
}
