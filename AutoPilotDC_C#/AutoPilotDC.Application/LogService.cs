using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Application;

public class LogService
{
    private readonly ILogRepository _repo;
    public LogService(ILogRepository repo) => _repo = repo;

    public void Add(LogEntry entry) => _repo.Add(entry);
    public IReadOnlyList<LogEntry> GetAll() => _repo.GetAll();
    public void Clear() => _repo.Clear();

    // Async (full names)
    public Task ExportJsonAsync(string path) => _repo.ExportJsonAsync(path);
    public Task ExportCsvAsync(string path) => _repo.ExportCsvAsync(path);
    public Task ExportXlsxAsync(string path) => _repo.ExportXlsxAsync(path);

    // Aliases fara Async (compatibilitate MainViewModel)
    public Task ExportXlsx() => _repo.ExportXlsxAsync(GetDefaultPath("xlsx"));
    public Task ExportCsv() => _repo.ExportCsvAsync(GetDefaultPath("csv"));
    public Task ExportJson() => _repo.ExportJsonAsync(GetDefaultPath("json"));

    private static string GetDefaultPath(string ext)
    {
        var dir = System.IO.Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "AutoPilotDC", "Logs");
        System.IO.Directory.CreateDirectory(dir);
        return System.IO.Path.Combine(dir,
            $"log_{DateTime.Now:yyyyMMdd_HHmmss}.{ext}");
    }
}