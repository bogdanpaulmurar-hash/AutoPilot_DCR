using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Services
{
    /// <summary>
    /// Gestioneaza configuratia persistenta (config.json).
    /// Thread-safe. La load, valorile lipsa se completeaza cu defaults.
    /// </summary>
    public class SettingsManager : ISettingsManager
    {
        private readonly string _configPath;
        private readonly object _lock = new();
        private AppSettings _data;

        private static readonly JsonSerializerOptions _writeOpts = new() { WriteIndented = true };
        private static readonly JsonSerializerOptions _readOpts = new() { PropertyNameCaseInsensitive = true };

        // -- Defaults (identic Python v3.9) ------------------------------------
        public static AppSettings BuildDefaults() => new()
        {
            Theme = "dark",
            StepDelay = 0.8,
            MouseMoveDelay = 0.05,
            RecordMouseMove = false,
            MouseMoveThreshold = 5,
            MaxStepsWarning = 50,
            AutoSave = true,
            FontSize = 12,
            PlaybackSpeed = 1.0,
            CountdownBeforePlay = 3,
            RepeatCount = 1,
            ShowFloatingControls = true,
            ShowEmergencyBtn = true,
            ActiveMonitor = 0,
            Shortcuts = new Dictionary<string, string>
            {
                ["start_rec"] = "F5",
                ["stop_rec"] = "F6",
                ["resume_play"] = "F3",
                ["play"] = "F7",
                ["pause"] = "F8",
                ["resume"] = "F8",
                ["stop_play"] = "F9",
                ["emergency"] = "F12",
                ["save"] = "Ctrl+S",
                ["new"] = "Ctrl+N",
                ["open"] = "Ctrl+O",
                ["add_delay"] = "Ctrl+D",
                ["add_step"] = "Ctrl+M",
                ["delete_step"] = "Delete",
                ["skip_step"] = "Ctrl+K",
                ["debug_step"] = "Ctrl+B",
                ["toggle_debug"] = "Ctrl+Shift+B",
                ["move_step_up"] = "Ctrl+Up",
                ["move_step_down"] = "Ctrl+Down",
                ["edit_step"] = "Ctrl+E",
                ["show_shortcuts"] = "Ctrl+H",
            }
        };

        public SettingsManager(string? configPath = null)
        {
            _configPath = configPath
                ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
            _data = BuildDefaults();
            Load();
        }

        // -- ISettingsManager --------------------------------------------------

        // FIX: proprietatea 'Current' ceruta de ISettingsManager
        public AppSettings Current
        {
            get { lock (_lock) return _data; }
        }

        public void Load()
        {
            lock (_lock)
            {
                _data = BuildDefaults();
                try
                {
                    if (!File.Exists(_configPath)) return;
                    var json = File.ReadAllText(_configPath);
                    var saved = JsonSerializer.Deserialize<AppSettings>(json, _readOpts);
                    if (saved == null) return;

                    if (!string.IsNullOrEmpty(saved.Theme)) _data.Theme = saved.Theme;
                    if (saved.StepDelay > 0) _data.StepDelay = saved.StepDelay;
                    if (saved.MouseMoveDelay > 0) _data.MouseMoveDelay = saved.MouseMoveDelay;
                    _data.RecordMouseMove = saved.RecordMouseMove;
                    if (saved.MouseMoveThreshold > 0) _data.MouseMoveThreshold = saved.MouseMoveThreshold;
                    if (saved.MaxStepsWarning > 0) _data.MaxStepsWarning = saved.MaxStepsWarning;
                    _data.AutoSave = saved.AutoSave;
                    if (saved.FontSize > 0) _data.FontSize = saved.FontSize;
                    if (saved.PlaybackSpeed > 0) _data.PlaybackSpeed = saved.PlaybackSpeed;
                    if (saved.CountdownBeforePlay >= 0) _data.CountdownBeforePlay = saved.CountdownBeforePlay;
                    if (saved.RepeatCount > 0) _data.RepeatCount = saved.RepeatCount;
                    _data.ShowFloatingControls = saved.ShowFloatingControls;
                    _data.ShowEmergencyBtn = saved.ShowEmergencyBtn;
                    _data.ActiveMonitor = saved.ActiveMonitor;
                    _data.DndDuringRun = saved.DndDuringRun;
                    _data.ShowRunFrame = saved.ShowRunFrame;
                    _data.GuardEnabled = saved.GuardEnabled;
                    if (!string.IsNullOrEmpty(saved.GuardSensitivity)) _data.GuardSensitivity = saved.GuardSensitivity;

                    if (saved.Shortcuts != null)
                        foreach (var kv in saved.Shortcuts)
                            _data.Shortcuts[kv.Key] = kv.Value;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Settings] Load failed: {ex.Message}");
                }
            }
        }

        public void Save()
        {
            lock (_lock)
            {
                try
                {
                    var json = JsonSerializer.Serialize(_data, _writeOpts);
                    File.WriteAllText(_configPath, json);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Settings] Save failed: {ex.Message}");
                }
            }
        }

        // FIX: ResetToDefaults() ceruta de ISettingsManager
        public void ResetToDefaults()
        {
            lock (_lock) { _data = BuildDefaults(); }
            Save();
        }

        public T Get<T>(string key, T defaultValue = default!)
        {
            try
            {
                var prop = typeof(AppSettings).GetProperty(
                    ToPascalCase(key),
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);

                if (prop != null)
                {
                    var val = prop.GetValue(Current);
                    if (val is T typed) return typed;
                    return (T)Convert.ChangeType(val!, typeof(T));
                }
            }
            catch { }
            return defaultValue;
        }

        public void Set<T>(string key, T value)
        {
            lock (_lock)
            {
                try
                {
                    var prop = typeof(AppSettings).GetProperty(
                        ToPascalCase(key),
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    prop?.SetValue(_data, value);
                }
                catch { }
            }
            Save();
        }

        public string GetShortcut(string action)
        {
            lock (_lock)
            {
                if (_data.Shortcuts.TryGetValue(action, out var val)) return val;
                var defs = BuildDefaults().Shortcuts;
                return defs.TryGetValue(action, out var def) ? def : string.Empty;
            }
        }

        public void SetShortcut(string action, string combo)
        {
            lock (_lock) { _data.Shortcuts[action] = combo; }
            Save();
        }

        // -- Helper ------------------------------------------------------------
        private static string ToPascalCase(string snake)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var p in snake.Split('_'))
                if (p.Length > 0) sb.Append(char.ToUpper(p[0]) + p[1..]);
            return sb.ToString();
        }
    }
}