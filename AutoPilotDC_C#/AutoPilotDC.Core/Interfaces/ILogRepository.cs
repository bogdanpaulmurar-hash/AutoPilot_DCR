// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// ILogRepository.cs - Contract pentru LogManager
// Echivalent Python: LogManager
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Contract pentru managementul log-urilor de executie.
/// Thread-safe, suporta export XLSX / CSV / JSON.
/// </summary>
public interface ILogRepository
{
    /// <summary>Adauga o intrare in log.</summary>
    void Add(LogEntry entry);

    /// <summary>Returneaza toate intrarile din log-ul curent.</summary>
    IReadOnlyList<LogEntry> GetAll();

    /// <summary>Goleste log-ul curent.</summary>
    void Clear();

    /// <summary>Exporta log-ul in format JSON.</summary>
    Task ExportJsonAsync(string filePath);

    /// <summary>Exporta log-ul in format CSV.</summary>
    Task ExportCsvAsync(string filePath);

    /// <summary>Exporta log-ul in format XLSX.</summary>
    Task ExportXlsxAsync(string filePath);
}