// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// ISettingsManager.cs - Contract pentru SettingsManager
// Echivalent Python: SettingsManager (config.json)
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Contract pentru managementul configuratiei persistente.
/// Citeste/scrie config.json cu fallback la valori default.
/// </summary>
public interface ISettingsManager
{
    /// <summary>Setarile curente incarcate.</summary>
    AppSettings Current { get; }

    /// <summary>Returneaza valoarea unui setting dupa cheie, cu fallback la default.</summary>
    T Get<T>(string key, T defaultValue = default!);

    /// <summary>Seteaza valoarea unui setting dupa cheie.</summary>
    void Set<T>(string key, T value);

    /// <summary>Incarca setarile din config.json (cu fallback la default).</summary>
    void Load();

    /// <summary>Salveaza setarile curente in config.json.</summary>
    void Save();

    /// <summary>Returneaza valoarea unui shortcut dupa action name.</summary>
    string GetShortcut(string action);

    /// <summary>Seteaza un shortcut pentru o actiune.</summary>
    void SetShortcut(string action, string combo);

    /// <summary>Reseteaza toate setarile la valorile default.</summary>
    void ResetToDefaults();
}