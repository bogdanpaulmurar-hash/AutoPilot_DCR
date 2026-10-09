// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// IRoutineRepository.cs - Contract pentru salvare/incarcare rutine
// Echivalent Python: RoutineManager
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Contract pentru persistenta rutinelor (JSON pe disc).
/// Compatibil cu rutinele salvate de Python v3.9.
/// </summary>
public interface IRoutineRepository
{
    /// <summary>Returneaza lista numelor tuturor rutinelor salvate.</summary>
    IReadOnlyList<string> GetRoutineNames();

    /// <summary>Incarca o rutina dupa nume. Null daca nu exista.</summary>
    RoutineFile? Load(string name);

    /// <summary>Salveaza o rutina pe disc (suprascrie daca exista).</summary>
    void Save(RoutineFile routine);

    /// <summary>Sterge o rutina dupa nume.</summary>
    bool Delete(string name);

    /// <summary>Redenumeste o rutina.</summary>
    bool Rename(string oldName, string newName);

    /// <summary>True daca exista o rutina cu numele dat.</summary>
    bool Exists(string name);
}