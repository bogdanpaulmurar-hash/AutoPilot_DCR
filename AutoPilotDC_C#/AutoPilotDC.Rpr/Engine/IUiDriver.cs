// ============================================================
// AutoPilot DC v4 — RPR
// IUiDriver.cs — Contractul comun pentru Web / Selenium / Desktop / SAP
// Motorul RPR nu stie cum se face un click in SAP sau in browser;
// stie doar sa ceara driverului potrivit.
// ============================================================

using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Engine;

/// <summary>Starea unui element la un moment dat.</summary>
public sealed record ElementState(
    bool Exists,
    bool Visible,
    bool Enabled,
    string Text,
    string Value,
    Locator? UsedLocator)
{
    public static readonly ElementState NotFound = new(false, false, false, "", "", null);
}

/// <summary>Cererea de executie a unei actiuni.</summary>
public sealed record ActionRequest(
    RprAction Action,
    UiObject? Target,
    string Value,
    int TimeoutMs,
    bool DirectMode,
    string OutputFolder);

/// <summary>Un driver de interfata (o tehnologie).</summary>
public interface IUiDriver : IAsyncDisposable
{
    UiTechnology Technology { get; }

    string DisplayName { get; }

    /// <summary>
    /// Cauta elementul (asteapta maxim timeoutMs) si returneaza starea.
    /// Nu arunca exceptie daca nu il gaseste — returneaza ElementState.NotFound.
    /// </summary>
    Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct);

    /// <summary>
    /// Executa actiunea. Returneaza valoarea citita (pentru Citeste...) sau null.
    /// Arunca <see cref="RprStepException"/> cu mesaj clar daca nu reuseste.
    /// </summary>
    Task<string?> ExecuteAsync(ActionRequest request, CancellationToken ct);

    /// <summary>Marcheaza vizual elementul (fara exceptii — best effort).</summary>
    Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct);

    /// <summary>Captura ecranului / paginii curente (pentru log la eroare). Returneaza calea sau null.</summary>
    Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct);
}

/// <summary>Driver care poate marca obiecte interactiv (Object Spy).</summary>
public interface ISpyCapable
{
    /// <summary>
    /// Porneste modul Spy: elementul de sub mouse e conturat; utilizatorul il captureaza.
    /// Returneaza obiectul capturat (cu locatori generati) sau null daca a anulat.
    /// </summary>
    Task<UiObject?> CaptureObjectAsync(SpyOptions options, CancellationToken ct);
}

public sealed class SpyOptions
{
    /// <summary>Folder unde se salveaza captura elementului.</summary>
    public string ScreenshotFolder { get; set; } = "";

    /// <summary>Mesaj afisat utilizatorului in timpul Spy.</summary>
    public string Hint { get; set; } = "";
}

/// <summary>Un pas inregistrat de recorder (click, scriere text, alegere optiune).</summary>
public sealed record RecordedAction(RprAction Action, UiObject Target, string Value);

/// <summary>Driver care poate inregistra actiuni pe obiecte (Recorder -> pasi reali).</summary>
public interface IRecordCapable
{
    bool IsRecording { get; }

    /// <summary>Porneste inregistrarea; fiecare actiune ajunge in callback.</summary>
    Task StartRecordingAsync(Action<RecordedAction> onAction, SpyOptions options, CancellationToken ct);

    Task StopRecordingAsync();
}

/// <summary>Furnizeaza driverul pentru o tehnologie (creat la prima folosire).</summary>
public interface IDriverProvider
{
    IUiDriver Get(UiTechnology technology);
}

/// <summary>Eroare intr-un pas, cu mesaj pentru utilizator.</summary>
public class RprStepException : Exception
{
    public RprStepException(string message, Exception? inner = null) : base(message, inner) { }
}

/// <summary>Elementul nu a fost gasit cu niciun locator.</summary>
public sealed class ElementNotFoundException : RprStepException
{
    public UiObject Object { get; }

    public ElementNotFoundException(UiObject obj, int timeoutMs, string? detail = null)
        : base(BuildMessage(obj, timeoutMs, detail))
    {
        Object = obj;
    }

    private static string BuildMessage(UiObject obj, int timeoutMs, string? detail)
    {
        var tried = string.Join("; ", obj.ActiveLocators.Select(l => l.ToString()));
        var msg = $"Obiectul [{obj.Name}] nu a fost gasit in {timeoutMs / 1000.0:0.#} s. Locatori incercati: {tried}";
        return string.IsNullOrWhiteSpace(detail) ? msg : $"{msg}. Detalii: {detail}";
    }
}
