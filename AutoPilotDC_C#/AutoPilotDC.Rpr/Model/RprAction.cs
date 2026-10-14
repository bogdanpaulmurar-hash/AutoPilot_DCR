// ============================================================
// AutoPilot DC v4 — RPR
// RprAction.cs — Actiunile pe care un pas le poate face
// + metadate pentru Studio (ce campuri arata fiecare actiune)
// ============================================================

namespace AutoPilotDC.Rpr.Model;

/// <summary>Actiunile disponibile intr-un pas "Actiune".</summary>
public enum RprAction
{
    // ── Pe un obiect (orice tehnologie) ──────────────────
    Click,
    DoubleClick,
    RightClick,
    Hover,
    TypeText,        // inlocuieste continutul campului
    AppendText,      // tasteaza caracter cu caracter, fara stergere
    Clear,
    PressKey,        // ex: Enter, Tab, Ctrl+A (pe obiect sau global)
    SelectOption,    // dropdown / combo: dupa text vizibil
    Check,
    Uncheck,
    Focus,
    ReadText,        // text vizibil -> variabila
    ReadValue,       // valoarea campului -> variabila
    ReadAttribute,   // atribut (Valoare = numele atributului) -> variabila
    Highlight,       // doar marcheaza elementul (verificare vizuala)
    ScreenshotElement,

    // ── Browser (fara obiect) ─────────────────────────────
    OpenBrowser,     // Valoare = URL de start
    Navigate,        // Valoare = URL
    Back,
    Refresh,
    SwitchTab,       // Valoare = index (0,1..) sau fragment din titlu/URL
    HandleDialog,    // Valoare = accept / dismiss — pentru alert/confirm JS
    ScreenshotPage,
    CloseBrowser,

    // ── SAP GUI (fara obiect sau cu obiect) ───────────────
    SapConnect,          // se ataseaza la sesiunea SAP deschisa (Valoare = index sesiune, optional)
    SapTransaction,      // Valoare = cod tranzactie (ex: VA03)
    SapSendKey,          // Valoare = Enter / F3 / F8 / Ctrl+S ...
    SapReadStatusBar,    // mesajul din bara de stare -> variabila
    SapGridReadCell,     // obiect = grid/tabel, Valoare = "rand|coloana"
    SapGridRowCount,     // obiect = grid/tabel -> variabila

    // ── Desktop (fara obiect) ─────────────────────────────
    LaunchApp,           // Valoare = cale .exe [argumente]
    AttachWindow,        // Valoare = titlu fereastra (regex) sau proces:nume.exe
    CloseWindow,
}

/// <summary>Descrierea unei actiuni pentru Studio (ce campuri sunt necesare).</summary>
public sealed record ActionInfo(
    RprAction Action,
    string Label,
    bool NeedsTarget,
    bool TargetOptional,
    string? ValueLabel,
    bool ProducesOutput,
    UiTechnology[] Technologies);

/// <summary>Catalogul de actiuni. Studio construieste dropdown-urile din el.</summary>
public static class ActionCatalog
{
    private static readonly UiTechnology[] All = { UiTechnology.Web, UiTechnology.WebSelenium, UiTechnology.Desktop, UiTechnology.Sap };
    private static readonly UiTechnology[] WebOnly = { UiTechnology.Web, UiTechnology.WebSelenium };
    private static readonly UiTechnology[] SapOnly = { UiTechnology.Sap };
    private static readonly UiTechnology[] DesktopOnly = { UiTechnology.Desktop };

    public static readonly IReadOnlyList<ActionInfo> Actions = new List<ActionInfo>
    {
        new(RprAction.Click,             "Click",                      true,  false, null,                    false, All),
        new(RprAction.DoubleClick,       "Dublu click",                true,  false, null,                    false, All),
        new(RprAction.RightClick,        "Click dreapta",              true,  false, null,                    false, All),
        new(RprAction.Hover,             "Mouse deasupra",             true,  false, null,                    false, All),
        new(RprAction.TypeText,          "Scrie text (inlocuieste)",   true,  false, "Text",                  false, All),
        new(RprAction.AppendText,        "Tasteaza text (adauga)",     true,  false, "Text",                  false, All),
        new(RprAction.Clear,             "Goleste campul",             true,  false, null,                    false, All),
        new(RprAction.PressKey,          "Apasa tasta",                false, true,  "Tasta (Enter, Tab, Ctrl+A...)", false, All),
        new(RprAction.SelectOption,      "Alege din lista",            true,  false, "Optiune (text)",        false, All),
        new(RprAction.Check,             "Bifeaza",                    true,  false, null,                    false, All),
        new(RprAction.Uncheck,           "Debifeaza",                  true,  false, null,                    false, All),
        new(RprAction.Focus,             "Focus",                      true,  false, null,                    false, All),
        new(RprAction.ReadText,          "Citeste textul",             true,  false, null,                    true,  All),
        new(RprAction.ReadValue,         "Citeste valoarea",           true,  false, null,                    true,  All),
        new(RprAction.ReadAttribute,     "Citeste atribut",            true,  false, "Nume atribut",          true,  All),
        new(RprAction.Highlight,         "Marcheaza (verificare)",     true,  false, null,                    false, All),
        new(RprAction.ScreenshotElement, "Captura element",            true,  false, "Fisier (optional)",     true,  All),

        new(RprAction.OpenBrowser,       "Deschide browser",           false, false, "URL de start",          false, WebOnly),
        new(RprAction.Navigate,          "Mergi la URL",               false, false, "URL",                   false, WebOnly),
        new(RprAction.Back,              "Inapoi",                     false, false, null,                    false, WebOnly),
        new(RprAction.Refresh,           "Reincarca pagina",           false, false, null,                    false, WebOnly),
        new(RprAction.SwitchTab,         "Schimba tab-ul",             false, false, "Index sau text din titlu", false, WebOnly),
        new(RprAction.HandleDialog,      "Raspuns la popup JS",        false, false, "accept / dismiss",      false, WebOnly),
        new(RprAction.ScreenshotPage,    "Captura pagina",             false, false, "Fisier (optional)",     true,  WebOnly),
        new(RprAction.CloseBrowser,      "Inchide browser",            false, false, null,                    false, WebOnly),

        new(RprAction.SapConnect,        "SAP: conecteaza la sesiune", false, false, "Index sesiune (gol = prima)", false, SapOnly),
        new(RprAction.SapTransaction,    "SAP: porneste tranzactie",   false, false, "Cod tranzactie",        false, SapOnly),
        new(RprAction.SapSendKey,        "SAP: trimite tasta",         false, false, "Tasta (Enter, F3, F8...)", false, SapOnly),
        new(RprAction.SapReadStatusBar,  "SAP: citeste bara de stare", false, false, null,                    true,  SapOnly),
        new(RprAction.SapGridReadCell,   "SAP: citeste celula tabel",  true,  false, "rand|coloana",          true,  SapOnly),
        new(RprAction.SapGridRowCount,   "SAP: numar randuri tabel",   true,  false, null,                    true,  SapOnly),

        new(RprAction.LaunchApp,         "Porneste aplicatie",         false, false, "Cale .exe [argumente]", false, DesktopOnly),
        new(RprAction.AttachWindow,      "Ataseaza fereastra",         false, false, "Titlu (regex) sau proces:nume.exe", false, DesktopOnly),
        new(RprAction.CloseWindow,       "Inchide fereastra",          false, false, null,                    false, DesktopOnly),
    };

    public static ActionInfo Get(RprAction action) => Actions.First(a => a.Action == action);
}
