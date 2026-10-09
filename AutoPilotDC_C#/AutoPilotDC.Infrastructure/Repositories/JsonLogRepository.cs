using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;
using ClosedXML.Excel;

namespace AutoPilotDC.Infrastructure.Repositories
{
    /// <summary>
    /// Gestioneaza log-urile de executie in loguri/.
    /// Fiecare sesiune = un fisier JSON per zi (log_YYYYMMDD.json).
    /// Suporta export JSON / CSV / XLSX.
    /// </summary>
    public class JsonLogRepository : ILogRepository
    {
        private readonly string _dir;
        private readonly object _lock = new();

        private static readonly JsonSerializerOptions _writeOpts = new()
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        };
        private static readonly JsonSerializerOptions _readOpts = new()
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        };

        public JsonLogRepository(string? directory = null)
        {
            _dir = directory
                ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "loguri");
            Directory.CreateDirectory(_dir);
        }

        public void Add(LogEntry entry)
        {
            lock (_lock)
            {
                var list = LoadSession();
                list.Add(entry);
                SaveSession(list);
            }
        }

        public IReadOnlyList<LogEntry> GetAll()
        {
            lock (_lock) { return LoadSession().AsReadOnly(); }
        }

        public void Clear()
        {
            lock (_lock) { SaveSession(new List<LogEntry>()); }
        }

        public async Task ExportJsonAsync(string path)
        {
            IReadOnlyList<LogEntry> entries;
            lock (_lock) { entries = LoadSession().AsReadOnly(); }
            var json = JsonSerializer.Serialize(entries, _writeOpts);
            await File.WriteAllTextAsync(path, json, Encoding.UTF8);
        }

        public async Task ExportCsvAsync(string path)
        {
            IReadOnlyList<LogEntry> entries;
            lock (_lock) { entries = LoadSession().AsReadOnly(); }

            var sb = new StringBuilder();
            sb.AppendLine("entry_id,timestamp,step_id,action,result,has_error,error_msg,comment,duration_ms,iteration");
            foreach (var e in entries)
            {
                sb.AppendLine(string.Join(",",
                    e.EntryId,
                    CsvEscape(e.Timestamp),
                    e.StepId,
                    CsvEscape(e.Action),
                    CsvEscape(e.Result),
                    e.HasError,
                    CsvEscape(e.ErrorMsg),
                    CsvEscape(e.Comment),
                    e.DurationMs,
                    e.Iteration));
            }
            await File.WriteAllTextAsync(path, sb.ToString(), Encoding.UTF8);
        }

        public Task ExportXlsxAsync(string path)
        {
            IReadOnlyList<LogEntry> entries;
            lock (_lock) { entries = LoadSession().AsReadOnly(); }

            using var wb = new XLWorkbook();
            var ws = wb.Worksheets.Add("Log");

            string[] headers = { "ID", "Timestamp", "Step ID", "Action", "Result",
                                  "Error", "Error Msg", "Comment", "Duration (ms)", "Iteration" };
            for (int i = 0; i < headers.Length; i++)
            {
                ws.Cell(1, i + 1).Value = headers[i];
                ws.Cell(1, i + 1).Style.Font.Bold = true;
                ws.Cell(1, i + 1).Style.Fill.BackgroundColor = XLColor.FromHtml("#009999");
                ws.Cell(1, i + 1).Style.Font.FontColor = XLColor.White;
            }

            for (int r = 0; r < entries.Count; r++)
            {
                var e = entries[r];
                int row = r + 2;
                ws.Cell(row, 1).Value = e.EntryId;
                ws.Cell(row, 2).Value = e.Timestamp;
                ws.Cell(row, 3).Value = e.StepId;
                ws.Cell(row, 4).Value = e.Action;
                ws.Cell(row, 5).Value = e.Result;
                ws.Cell(row, 6).Value = e.HasError;
                ws.Cell(row, 7).Value = e.ErrorMsg;
                ws.Cell(row, 8).Value = e.Comment;
                ws.Cell(row, 9).Value = e.DurationMs;
                ws.Cell(row, 10).Value = e.Iteration;

                if (e.HasError)
                    ws.Row(row).Style.Fill.BackgroundColor = XLColor.FromHtml("#FFCCCC");
            }

            ws.Columns().AdjustToContents();
            wb.SaveAs(path);
            return Task.CompletedTask;
        }

        // -- Extra helpers (non-interface) ------------------------------------
        public void AddRange(IEnumerable<LogEntry> entries)
        {
            lock (_lock)
            {
                var list = LoadSession();
                list.AddRange(entries);
                SaveSession(list);
            }
        }

        public IEnumerable<string> GetSessionFiles() =>
            Directory.EnumerateFiles(_dir, "log_*.json").OrderByDescending(f => f);

        public List<LogEntry> LoadSession(string filePath)
        {
            try
            {
                return JsonSerializer.Deserialize<List<LogEntry>>(
                    File.ReadAllText(filePath), _readOpts) ?? new();
            }
            catch { return new(); }
        }

        // -- Private ----------------------------------------------------------
        private string CurrentSessionPath() =>
            Path.Combine(_dir, $"log_{DateTime.Now:yyyyMMdd}.json");

        private List<LogEntry> LoadSession()
        {
            var path = CurrentSessionPath();
            if (!File.Exists(path)) return new();
            try
            {
                return JsonSerializer.Deserialize<List<LogEntry>>(
                    File.ReadAllText(path), _readOpts) ?? new();
            }
            catch { return new(); }
        }

        private void SaveSession(List<LogEntry> entries)
        {
            try { File.WriteAllText(CurrentSessionPath(), JsonSerializer.Serialize(entries, _writeOpts)); }
            catch (Exception ex) { Console.WriteLine($"[Log] Save failed: {ex.Message}"); }
        }

        private static string CsvEscape(string? s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            if (s.Contains(',') || s.Contains('"') || s.Contains('\n') || s.Contains('\r'))
                return $"\"{s.Replace("\"", "\"\"")}\"";
            return s;
        }
    }
}