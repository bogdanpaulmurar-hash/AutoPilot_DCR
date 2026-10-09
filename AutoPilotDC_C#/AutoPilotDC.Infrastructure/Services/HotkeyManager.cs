// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// HotkeyManager.cs � Hotkeys globale via RegisterHotKey Win32
// FARA dependen?e WPF � func?ioneaza �n Infrastructure (non-WPF)
// Echivalent Python: HotkeyManager (hotkeys/__init__.py)
// ============================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Services;

/// <summary>
/// Gestioneaza hotkey-urile globale ale aplica?iei via RegisterHotKey Win32.
/// Nu depinde de WPF � prime?te HWND ca IntPtr din UI layer.
/// Echivalent Python: HotkeyManager (pynput.GlobalHotKeys).
/// 
/// Utilizare din UI (App.xaml.cs sau MainWindow.Loaded):
///   var hwnd = new WindowInteropHelper(this).Handle;
///   hotkeyManager.Initialize(hwnd, Dispatcher);
/// </summary>
public sealed class HotkeyManager : IDisposable
{
    // -- Win32 ------------------------------------------------------------
    private const int WM_HOTKEY = 0x0312;
    private const int WM_DESTROY = 0x0002;
    private const int WM_QUIT = 0x0012;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id,
                                               uint fsModifiers, uint vk);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    [DllImport("user32.dll")]
    private static extern bool GetMessage(out MSG lpMsg, IntPtr hWnd,
                                           uint wMsgFilterMin, uint wMsgFilterMax);
    [DllImport("user32.dll")]
    private static extern bool TranslateMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    private static extern IntPtr DispatchMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    private static extern bool PostThreadMessage(uint idThread, uint msg,
                                                  IntPtr wParam, IntPtr lParam);

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    [StructLayout(LayoutKind.Sequential)]
    private struct MSG
    {
        public IntPtr hwnd;
        public uint message;
        public IntPtr wParam;
        public IntPtr lParam;
        public uint time;
        public int pt_x;
        public int pt_y;
    }

    // Modifier flags
    private const uint MOD_NONE = 0x0000;
    private const uint MOD_ALT = 0x0001;
    private const uint MOD_CONTROL = 0x0002;
    private const uint MOD_SHIFT = 0x0004;
    private const uint MOD_WIN = 0x0008;
    private const uint MOD_NOREPEAT = 0x4000;

    // VK map
    private static readonly Dictionary<string, uint> _vkMap =
        new(StringComparer.OrdinalIgnoreCase)
        {
            ["F1"] = 0x70,
            ["F2"] = 0x71,
            ["F3"] = 0x72,
            ["F4"] = 0x73,
            ["F5"] = 0x74,
            ["F6"] = 0x75,
            ["F7"] = 0x76,
            ["F8"] = 0x77,
            ["F9"] = 0x78,
            ["F10"] = 0x79,
            ["F11"] = 0x7A,
            ["F12"] = 0x7B,
            ["A"] = 0x41,
            ["B"] = 0x42,
            ["C"] = 0x43,
            ["D"] = 0x44,
            ["E"] = 0x45,
            ["F"] = 0x46,
            ["G"] = 0x47,
            ["H"] = 0x48,
            ["I"] = 0x49,
            ["J"] = 0x4A,
            ["K"] = 0x4B,
            ["L"] = 0x4C,
            ["M"] = 0x4D,
            ["N"] = 0x4E,
            ["O"] = 0x4F,
            ["P"] = 0x50,
            ["Q"] = 0x51,
            ["R"] = 0x52,
            ["S"] = 0x53,
            ["T"] = 0x54,
            ["U"] = 0x55,
            ["V"] = 0x56,
            ["W"] = 0x57,
            ["X"] = 0x58,
            ["Y"] = 0x59,
            ["Z"] = 0x5A,
            ["DELETE"] = 0x2E,
            ["INSERT"] = 0x2D,
            ["HOME"] = 0x24,
            ["END"] = 0x23,
            ["PAGEUP"] = 0x21,
            ["PAGEDOWN"] = 0x22,
            ["UP"] = 0x26,
            ["DOWN"] = 0x28,
            ["LEFT"] = 0x25,
            ["RIGHT"] = 0x27,
            ["SPACE"] = 0x20,
            ["RETURN"] = 0x0D,
            ["ESCAPE"] = 0x1B,
            ["TAB"] = 0x09,
        };

    // -- State -------------------------------------------------------------
    private readonly ISettingsManager _settings;
    private readonly Dictionary<int, Action> _callbacks = new();
    private int _nextId = 1;
    private IntPtr _hwnd = IntPtr.Zero;
    private Action<Action>? _uiInvoke;   // UI dispatcher inject
    private readonly object _lock = new();
    private bool _initialized;  // used as guard in WndProcHook

    // -- Events publice ----------------------------------------------------
    public event Action? StartRecording;
    public event Action? StopRecording;
    public event Action? Play;
    public event Action? ResumePlay;
    public event Action? PauseResume;
    public event Action? StopPlay;
    public event Action? EmergencyStop;

    // -- Constructor -------------------------------------------------------
    public HotkeyManager(ISettingsManager settings)
    {
        _settings = settings;
    }

    // -- API publica -------------------------------------------------------

    /// <summary>
    /// Ini?ializeaza HotkeyManager.
    /// Apelat din MainWindow.Loaded cu HWND-ul ferestrei ?i un UI dispatcher.
    /// 
    /// Exemplu din MainWindow.xaml.cs:
    ///   var hwnd = new WindowInteropHelper(this).Handle;
    ///   _hotkeyManager.Initialize(hwnd, action => Dispatcher.InvokeAsync(action));
    ///   // Adauga hook WndProc pentru WM_HOTKEY:
    ///   HwndSource.FromHwnd(hwnd).AddHook(_hotkeyManager.WndProcHook);
    /// </summary>
    public void Initialize(IntPtr hwnd, Action<Action> uiInvoke)
    {
        _hwnd = hwnd;
        _uiInvoke = uiInvoke;
        RegisterAllHotkeys();
        _initialized = true;
    }

    /// <summary>
    /// WndProc hook � adaugat de UI layer via HwndSource.AddHook().
    /// Proceseaza WM_HOTKEY ?i apeleaza callback-ul corespunzator pe UI thread.
    /// </summary>
    public IntPtr WndProcHook(IntPtr hwnd, int msg, IntPtr wParam,
                               IntPtr lParam, ref bool handled)
    {
        if (!_initialized) return IntPtr.Zero;
        if (msg == WM_HOTKEY)
        {
            int id = wParam.ToInt32();
            Action? cb;
            lock (_lock) _callbacks.TryGetValue(id, out cb);

            if (cb != null)
            {
                // Executa pe UI thread (identic Python: root.after(0, callback))
                _uiInvoke?.Invoke(cb);
                handled = true;
            }
        }
        return IntPtr.Zero;
    }

    /// <summary>Re-�nregistreaza toate hotkey-urile (dupa schimbarea setarilor).</summary>
    public void Reload()
    {
        UnregisterAll();
        RegisterAllHotkeys();
    }

    /// <summary>Dezregistreaza toate hotkey-urile.</summary>
    public void UnregisterAll()
    {
        lock (_lock)
        {
            foreach (var id in _callbacks.Keys)
                UnregisterHotKey(_hwnd, id);
            _callbacks.Clear();
            _nextId = 1;
        }
    }

    // -- �nregistrare -----------------------------------------------------

    private void RegisterAllHotkeys()
    {
        if (_hwnd == IntPtr.Zero) return;

        _settings.Load();

        var appSettings = _settings.Current;
        var sc = appSettings.Shortcuts;

        // Identic Python: _register_hotkeys()
        Register(sc.GetValueOrDefault("start_rec", "F5"), () => StartRecording?.Invoke());
        Register(sc.GetValueOrDefault("stop_rec", "F6"), () => StopRecording?.Invoke());
        Register(sc.GetValueOrDefault("play", "F7"), () => Play?.Invoke());
        Register(sc.GetValueOrDefault("resume_play", "F3"), () => ResumePlay?.Invoke());
        Register(sc.GetValueOrDefault("pause", "F8"), () => PauseResume?.Invoke());
        Register(sc.GetValueOrDefault("stop_play", "F9"), () => StopPlay?.Invoke());
        Register(sc.GetValueOrDefault("emergency", "F12"), () => EmergencyStop?.Invoke());
    }

    private void Register(string combo, Action callback)
    {
        if (!ParseCombo(combo, out uint modifiers, out uint vk)) return;

        lock (_lock)
        {
            int id = _nextId++;
            bool ok = RegisterHotKey(_hwnd, id, modifiers | MOD_NOREPEAT, vk);
            if (ok)
                _callbacks[id] = callback;
            else
                Debug.WriteLine(
                    $"[HotkeyManager] RegisterHotKey e?uat '{combo}': {Marshal.GetLastWin32Error()}");
        }
    }

    // -- Parser combo -----------------------------------------------------

    private static bool ParseCombo(string combo, out uint modifiers, out uint vk)
    {
        modifiers = MOD_NONE;
        vk = 0;

        if (string.IsNullOrWhiteSpace(combo)) return false;

        var parts = combo.Split('+', StringSplitOptions.RemoveEmptyEntries);
        string key = parts[^1].Trim();

        foreach (var part in parts[..^1])
        {
            switch (part.Trim().ToUpperInvariant())
            {
                case "CTRL": modifiers |= MOD_CONTROL; break;
                case "SHIFT": modifiers |= MOD_SHIFT; break;
                case "ALT": modifiers |= MOD_ALT; break;
                case "WIN": modifiers |= MOD_WIN; break;
            }
        }

        if (_vkMap.TryGetValue(key.ToUpperInvariant(), out uint found))
        {
            vk = found;
            return true;
        }

        if (key.Length == 1)
        {
            vk = (uint)char.ToUpperInvariant(key[0]);
            return true;
        }

        return false;
    }

    public void Dispose() => UnregisterAll();
}