// ============================================================
// AutoPilot DC v4 — Studio RPR
// StudioServices.cs — Setari Studio, furnizorul de drivere,
// elementul de arbore (NodeItem).
// ============================================================

using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text.Json;
using AutoPilotDC.Drivers.Web;
using AutoPilotDC.Drivers.Windows;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;
using AutoPilotDC.Rpr.Storage;

namespace AutoPilotDC.UI.Studio;

// ─────────────────────────────────────────────────────────────
// Setari Studio (persistente)
// ─────────────────────────────────────────────────────────────
public sealed class StudioSettings
{
    public BrowserKind Browser { get; set; } = BrowserKind.Edge;
    public bool Headless { get; set; }

    /// <summary>Minimizeaza Studio cand pornesti rularea (ramane bara plutitoare de control).</summary>
    public bool MinimizeOnRun { get; set; } = true;

    public string LastRoutinePath { get; set; } = "";

    private static string FilePath => Path.Combine(RprPaths.Root, "studio-setari.json");

    public static StudioSettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
                return JsonSerializer.Deserialize<StudioSettings>(File.ReadAllText(FilePath), RprJson.Options) ?? new();
        }
        catch (Exception) { /* fisier corupt: pornim cu setari implicite */ }
        return new StudioSettings();
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(RprPaths.Root);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(this, RprJson.Options));
        }
        catch (Exception) { }
    }
}

// ─────────────────────────────────────────────────────────────
// Drivere: create la prima folosire, pastrate intre rulari
// (browserul ramane deschis -> Spy si rularea lucreaza pe aceeasi pagina)
// ─────────────────────────────────────────────────────────────
public sealed class StudioDriverProvider : IDriverProvider, IAsyncDisposable
{
    private readonly StudioSettings _settings;
    private PlaywrightUiDriver? _web;
    private SeleniumUiDriver? _selenium;
    private DesktopUiDriver? _desktop;
    private SapUiDriver? _sap;

    public event Action<string>? Info;

    public StudioDriverProvider(StudioSettings settings) => _settings = settings;

    private WebDriverSettings WebSettings => new()
    {
        Browser = _settings.Browser,
        Headless = _settings.Headless,
        ProfileFolder = RprPaths.BrowserProfile,
    };

    public PlaywrightUiDriver Web
    {
        get
        {
            if (_web == null)
            {
                _web = new PlaywrightUiDriver(WebSettings);
                _web.Info += m => Info?.Invoke(m);
            }
            return _web;
        }
    }

    public SeleniumUiDriver Selenium
    {
        get
        {
            if (_selenium == null)
            {
                _selenium = new SeleniumUiDriver(WebSettings);
                _selenium.Info += m => Info?.Invoke(m);
            }
            return _selenium;
        }
    }

    public DesktopUiDriver Desktop => _desktop ??= new DesktopUiDriver();
    public SapUiDriver Sap => _sap ??= new SapUiDriver();

    public IUiDriver Get(UiTechnology technology) => technology switch
    {
        UiTechnology.Web         => Web,
        UiTechnology.WebSelenium => Selenium,
        UiTechnology.Desktop     => Desktop,
        UiTechnology.Sap         => Sap,
        _ => throw new RprStepException($"Tehnologie necunoscuta: {technology}"),
    };

    /// <summary>Dupa schimbarea browserului din setari: inchidem driverele web vechi.</summary>
    public async Task ResetWebAsync()
    {
        if (_web != null) await _web.DisposeAsync();
        if (_selenium != null) await _selenium.DisposeAsync();
        _web = null;
        _selenium = null;
    }

    public async ValueTask DisposeAsync()
    {
        await ResetWebAsync();
        if (_desktop != null) await _desktop.DisposeAsync();
        if (_sap != null) await _sap.DisposeAsync();
    }
}

// ─────────────────────────────────────────────────────────────
// Element din arborele rutinei: un pas sau o ramura (Atunci / Altfel...)
// ─────────────────────────────────────────────────────────────
public enum NodeRunState { None, Running, Ok, Error }

public sealed class NodeItem : INotifyPropertyChanged
{
    /// <summary>Pasul (null pentru o ramura).</summary>
    public RprNode? Node { get; }

    /// <summary>Lista care contine pasul (sau, pentru o ramura, lista ramurii).</summary>
    public List<RprNode> OwnerList { get; }

    /// <summary>Numele ramurii (doar pentru elemente-ramura).</summary>
    public string? Branch { get; }

    public NodeItem? Parent { get; }

    public ObservableCollection<NodeItem> Children { get; } = new();

    public bool IsBranch => Node == null;

    public NodeItem(RprNode? node, List<RprNode> ownerList, string? branch, NodeItem? parent)
    {
        Node = node;
        OwnerList = ownerList;
        Branch = branch;
        Parent = parent;
    }

    public string Icon => Node != null ? StudioLabels.IconFor(Node) : "↳";

    public string Title => Node?.Title ?? (Branch + (OwnerList.Count == 0 ? "  (gol — selecteaza si adauga pasi)" : ""));

    public string Kind => Node?.KindLabel ?? "";

    public string Comment => Node?.Comment ?? "";

    public bool HasComment => !string.IsNullOrWhiteSpace(Comment);

    public double ItemOpacity => Node == null || Node.Enabled ? 1.0 : 0.45;

    public string Number => Node == null ? "" : (OwnerList.IndexOf(Node) + 1) + ".";

    private bool _isExpanded = true;
    public bool IsExpanded { get => _isExpanded; set { _isExpanded = value; OnChanged(); } }

    private bool _isSelected;
    public bool IsSelected { get => _isSelected; set { _isSelected = value; OnChanged(); } }

    private NodeRunState _state;
    public NodeRunState State { get => _state; set { _state = value; OnChanged(); } }

    /// <summary>Recalculeaza textele afisate dupa o modificare in proprietati.</summary>
    public void Refresh()
    {
        OnChanged(nameof(Title));
        OnChanged(nameof(Icon));
        OnChanged(nameof(Comment));
        OnChanged(nameof(HasComment));
        OnChanged(nameof(ItemOpacity));
        OnChanged(nameof(Number));
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

/// <summary>Un rand din logul de rulare afisat in Studio.</summary>
public sealed class LogRow
{
    public required RunLogEntry Entry { get; init; }
    public string Time => Entry.Time.ToString("HH:mm:ss");
    public string Level => Entry.Level switch { RprLogLevel.Error => "EROARE", RprLogLevel.Warning => "ATENTIE", _ => "info" };
    public string Row => Entry.ExcelRow > 0 ? $"r{Entry.ExcelRow}" : "";
    public string Step => Entry.NodeTitle;
    public string Message => Entry.Message;
    public bool IsError => Entry.Level == RprLogLevel.Error;
    public bool IsWarning => Entry.Level == RprLogLevel.Warning;
}
