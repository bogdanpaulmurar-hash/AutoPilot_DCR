using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Repositories
{
    /// <summary>
    /// Salveaza/incarca rutine ca JSON in rutine_salvate/.
    /// Format identic cu Python v3.9 pentru compatibilitate.
    /// </summary>
    public class JsonRoutineRepository : IRoutineRepository
    {
        private readonly string _dir;

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

        public JsonRoutineRepository(string? directory = null)
        {
            _dir = directory
                ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "rutine_salvate");
            Directory.CreateDirectory(_dir);
        }

        public IReadOnlyList<string> GetRoutineNames() =>
            Directory.EnumerateFiles(_dir, "*.json")
                .Select(f => Path.GetFileNameWithoutExtension(f))
                .OrderBy(n => n)
                .ToList()
                .AsReadOnly();

        public RoutineFile? Load(string name)
        {
            var path = FindFile(name);
            if (path == null) return null;
            try
            {
                var json = File.ReadAllText(path);
                return JsonSerializer.Deserialize<RoutineFile>(json, _readOpts);
            }
            catch { return null; }
        }

        public void Save(RoutineFile routine)
        {
            if (string.IsNullOrWhiteSpace(routine.Name))
                throw new ArgumentException("RoutineFile.Name nu poate fi gol.");

            routine.CreatedAt ??= DateTime.Now.ToString("o");
            routine.StepCount = routine.Steps?.Count ?? 0;

            var json = JsonSerializer.Serialize(routine, _writeOpts);
            File.WriteAllText(Path.Combine(_dir, $"{SafeName(routine.Name)}.json"), json);
        }

        public bool Delete(string name)
        {
            var path = FindFile(name);
            if (path == null) return false;
            File.Delete(path);
            return true;
        }

        public bool Rename(string oldName, string newName)
        {
            var src = FindFile(oldName);
            if (src == null) return false;
            var dst = Path.Combine(_dir, $"{SafeName(newName)}.json");
            File.Move(src, dst, overwrite: true);
            return true;
        }

        public bool Exists(string name) => FindFile(name) != null;

        public IEnumerable<RoutineFile> GetAllMetadata()
        {
            foreach (var file in Directory.EnumerateFiles(_dir, "*.json").OrderBy(f => f))
            {
                RoutineFile? rf = null;
                try
                {
                    rf = JsonSerializer.Deserialize<RoutineFile>(
                        File.ReadAllText(file), _readOpts);
                }
                catch { }
                if (rf != null) yield return rf;
            }
        }

        // -- Helpers ----------------------------------------------------------
        private string? FindFile(string name)
        {
            var safe = SafeName(name);
            var exact = Path.Combine(_dir, $"{safe}.json");
            if (File.Exists(exact)) return exact;
            return Directory.EnumerateFiles(_dir, "*.json")
                .FirstOrDefault(f => string.Equals(
                    Path.GetFileNameWithoutExtension(f), safe,
                    StringComparison.OrdinalIgnoreCase));
        }

        private static string SafeName(string name) =>
            string.Concat(name.Select(c =>
                Path.GetInvalidFileNameChars().Contains(c) ? '_' : c));
    }
}