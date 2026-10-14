// ============================================================
// AutoPilot DC v4 — RPR
// UiObject.cs — Obiect din Object Repository (stil SilkTest)
// Un obiect = un element de interfata (buton, camp, tabel...)
// marcat o singura data cu Spy si refolosit in orice rutina.
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Rpr.Model;

/// <summary>Tehnologia prin care este gasit un obiect.</summary>
public enum UiTechnology
{
    /// <summary>Pagina web prin Playwright (recomandat).</summary>
    Web,
    /// <summary>Pagina web prin Selenium WebDriver.</summary>
    WebSelenium,
    /// <summary>Aplicatie desktop Windows prin UI Automation (FlaUI).</summary>
    Desktop,
    /// <summary>SAP GUI prin SAP GUI Scripting.</summary>
    Sap,
}

/// <summary>Tipul unui locator. Ordinea din lista obiectului = ordinea de incercare.</summary>
public enum LocatorKind
{
    // ── Web ──────────────────────────────────────────────
    TestId,       // data-testid / data-test / data-qa
    Id,           // atribut id
    Role,         // rol ARIA + nume accesibil, valoare: "button|Salveaza"
    Label,        // eticheta asociata campului
    Placeholder,  // placeholder
    Name,         // atribut name
    Text,         // text vizibil
    Css,          // selector CSS
    XPath,        // XPath

    // ── Desktop (UI Automation) ──────────────────────────
    AutomationId,
    UiaName,      // Name + optional ControlType, valoare: "Button|OK"
    ClassName,
    UiaPath,      // cale in arbore: "Pane[0]/Button[name=OK]"

    // ── SAP GUI ──────────────────────────────────────────
    SapId,        // ex: wnd[0]/usr/ctxtRSYST-BNAME
    SapName,      // nume + tip, valoare: "RSYST-BNAME|GuiCTextField"
}

/// <summary>Un mod de a gasi elementul. Un obiect are mai multe (fallback / self-healing).</summary>
public sealed class Locator
{
    public LocatorKind Kind { get; set; }
    public string Value { get; set; } = "";

    /// <summary>Scor de stabilitate 0-100 calculat la capturare (mai mare = mai stabil).</summary>
    public int Score { get; set; }

    /// <summary>Locatorul poate fi dezactivat manual din Studio fara a fi sters.</summary>
    public bool Enabled { get; set; } = true;

    public Locator() { }
    public Locator(LocatorKind kind, string value, int score = 50)
    {
        Kind = kind; Value = value; Score = score;
    }

    public override string ToString() => $"{Kind}: {Value}";
}

/// <summary>
/// Element de interfata salvat in Object Repository.
/// Rutinele se refera la el prin <see cref="Name"/>, nu prin coordonate.
/// </summary>
public sealed class UiObject
{
    /// <summary>Nume prietenos, unic in repository (ex: "Buton_Submit", "Camp_IBase").</summary>
    public string Name { get; set; } = "";

    public UiTechnology Technology { get; set; } = UiTechnology.Web;

    /// <summary>Locatori in ordinea de incercare.</summary>
    public List<Locator> Locators { get; set; } = new();

    /// <summary>
    /// Context in care traieste obiectul:
    ///  Web     -> fragment de URL (optional, doar informativ / validare)
    ///  Desktop -> titlul ferestrei (regex) sau "proces:nume.exe"
    ///  Sap     -> id fereastra (ex: wnd[0])
    /// </summary>
    public string Context { get; set; } = "";

    /// <summary>
    /// Web: lantul de iframe-uri (selectori CSS, de la pagina principala in jos).
    /// Gol daca elementul e in pagina principala.
    /// </summary>
    public List<string> FramePath { get; set; } = new();

    /// <summary>Tip element (button, input, GuiButton, Edit...) — informativ in Studio.</summary>
    public string ElementType { get; set; } = "";

    /// <summary>Textul vizibil la momentul capturarii (ajuta la recunoastere in Studio).</summary>
    public string CapturedText { get; set; } = "";

    /// <summary>Captura de ecran a elementului (cale relativa la folderul repository).</summary>
    public string Screenshot { get; set; } = "";

    /// <summary>Alte atribute capturate (pentru diagnostic si regenerare locatori).</summary>
    public Dictionary<string, string> Attributes { get; set; } = new();

    public string Description { get; set; } = "";

    public DateTime CapturedAt { get; set; } = DateTime.Now;

    /// <summary>Locatorii activi, in ordinea de incercare.</summary>
    [JsonIgnore]
    public IEnumerable<Locator> ActiveLocators => Locators.Where(l => l.Enabled && !string.IsNullOrWhiteSpace(l.Value));

    public override string ToString() => $"{Name} ({Technology})";
}
