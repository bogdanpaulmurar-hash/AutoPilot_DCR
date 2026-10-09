// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// KeyboardRecorder.cs � WH_KEYBOARD_LL low-level hook
// Echivalent Python: RecorderEngine._on_key_press / _on_key_release
// ============================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Recording;

/// <summary>
/// �nregistreaza evenimentele tastatura globale via WH_KEYBOARD_LL.
/// Logica identica Python:
///   - Modifier keys (Ctrl/Shift/Alt/Win) ? tracked �n set, NU �nregistrate ca pa?i
///   - Char printabil fara modificatori ? TYPE step
///   - Orice altceva ? KEY step (cu combo Ctrl+X, Shift+F1 etc.)
///   - F5/F6/F7/F8/F9/F12 ? FILTRATE (hotkeys aplica?ie)
/// </summary>
public sealed class KeyboardRecorder : IDisposable
{
    // -- Win32 ------------------------------------------------------------
    private const int WH_KEYBOARD_LL = 13;
    private const int WM_KEYDOWN = 0x0100;
    private const int WM_SYSKEYDOWN = 0x0104;
    private const int WM_KEYUP = 0x0101;
    private const int WM_SYSKEYUP = 0x0105;

    // Virtual Key codes
    private const int VK_LCONTROL = 0xA2;
    private const int VK_RCONTROL = 0xA3;
    private const int VK_LSHIFT = 0xA0;
    private const int VK_RSHIFT = 0xA1;
    private const int VK_LMENU = 0xA4;  // Alt st�nga
    private const int VK_RMENU = 0xA5;  // Alt dreapta
    private const int VK_LWIN = 0x5B;
    private const int VK_RWIN = 0x5C;
    private const int VK_CAPITAL = 0x14;  // CapsLock

    // Hotkeys aplica?ie � FILTRATE (identic Python: _ctrl_keys)
    private static readonly HashSet<int> _appHotkeys =
    [
        0x74, // F5
        0x75, // F6
        0x76, // F7
        0x77, // F8
        0x78, // F9
        0x7B, // F12
    ];

    // Modifier VK codes
    private static readonly HashSet<int> _modifierVks =
    [
        VK_LCONTROL, VK_RCONTROL,
        VK_LSHIFT,   VK_RSHIFT,
        VK_LMENU,    VK_RMENU,
        VK_LWIN,     VK_RWIN,
    ];

    [StructLayout(LayoutKind.Sequential)]
    private struct KBDLLHOOKSTRUCT
    {
        public uint vkCode;
        public uint scanCode;
        public uint flags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn,
                                                   IntPtr hMod, uint dwThreadId);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnhookWindowsHookEx(IntPtr hhk);

    [DllImport("user32.dll")]
    private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode,
                                                 IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll")]
    private static extern IntPtr GetModuleHandle(string lpModuleName);

    [DllImport("user32.dll")]
    private static extern bool GetMessage(out MSG lpMsg, IntPtr hWnd,
                                           uint wMsgFilterMin, uint wMsgFilterMax);
    [DllImport("user32.dll")]
    private static extern bool TranslateMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    private static extern IntPtr DispatchMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    private static extern int ToUnicode(uint wVirtKey, uint wScanCode,
                                         byte[] lpKeyState, StringBuilder pwszBuff,
                                         int cchBuff, uint wFlags);
    [DllImport("user32.dll")]
    private static extern bool GetKeyboardState(byte[] lpKeyState);

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

    // -- State -------------------------------------------------------------
    private IntPtr _hookHandle = IntPtr.Zero;
    private LowLevelKeyboardProc? _hookProc;
    private Thread? _hookThread;
    private volatile bool _running;

    // Modifier tracking (identic Python: _modifiers set)
    private readonly HashSet<int> _activeModifiers = new();
    private readonly object _modLock = new();

    // Recorder state
    private volatile bool _isRecording;
    private volatile bool _isPaused;

    // Timing (shared cu MouseRecorder prin RecorderEngine)
    private DateTime _lastTime = DateTime.UtcNow;

    // -- Events ------------------------------------------------------------
    public event Action<StepModel>? StepRecorded;

    // -- API publica -------------------------------------------------------

    public void Start()
    {
        if (_running) return;
        _running = true;
        _lastTime = DateTime.UtcNow;

        _hookThread = new Thread(HookThreadProc)
        {
            IsBackground = true,
            Name = "KeyboardHookThread"
        };
        _hookThread.Start();
    }

    public void Stop()
    {
        _running = false;
        if (_hookHandle != IntPtr.Zero)
        {
            UnhookWindowsHookEx(_hookHandle);
            _hookHandle = IntPtr.Zero;
        }
        _hookThread?.Join(2000);
    }

    public void SetState(bool isRecording, bool isPaused)
    {
        _isRecording = isRecording;
        _isPaused = isPaused;
        if (!isRecording)
        {
            lock (_modLock) _activeModifiers.Clear();
        }
    }

    /// <summary>
    /// Sincronizeaza timestamp-ul cu MouseRecorder
    /// (ambii folosesc acela?i _lastTime logic �n RecorderEngine).
    /// </summary>
    public void ResetTimer()
    {
        _lastTime = DateTime.UtcNow;
    }

    // -- Thread hook -------------------------------------------------------

    private void HookThreadProc()
    {
        using var curProcess = Process.GetCurrentProcess();
        using var curModule = curProcess.MainModule!;

        _hookProc = HookCallback;
        _hookHandle = SetWindowsHookEx(
            WH_KEYBOARD_LL,
            _hookProc,
            GetModuleHandle(curModule.ModuleName!),
            0);

        if (_hookHandle == IntPtr.Zero)
        {
            Debug.WriteLine($"[KeyboardRecorder] SetWindowsHookEx e?uat: {Marshal.GetLastWin32Error()}");
            return;
        }

        while (_running && GetMessage(out MSG msg, IntPtr.Zero, 0, 0))
        {
            TranslateMessage(ref msg);
            DispatchMessage(ref msg);
        }

        if (_hookHandle != IntPtr.Zero)
        {
            UnhookWindowsHookEx(_hookHandle);
            _hookHandle = IntPtr.Zero;
        }
    }

    // -- Hook callback -----------------------------------------------------

    private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0)
        {
            var kb = Marshal.PtrToStructure<KBDLLHOOKSTRUCT>(lParam);
            int vk = (int)kb.vkCode;
            int msg = wParam.ToInt32();

            bool isKeyDown = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
            bool isKeyUp = msg == WM_KEYUP || msg == WM_SYSKEYUP;

            // Tracking modifier keys (identic Python: _modifiers set)
            if (_modifierVks.Contains(vk))
            {
                lock (_modLock)
                {
                    if (isKeyDown) _activeModifiers.Add(vk);
                    else if (isKeyUp) _activeModifiers.Remove(vk);
                }
                return CallNextHookEx(_hookHandle, nCode, wParam, lParam);
            }

            // Procesam doar KeyDown
            if (isKeyDown && _isRecording && !_isPaused)
            {
                // Filtram hotkeys aplica?ie (F5/F6/F7/F8/F9/F12)
                if (!_appHotkeys.Contains(vk))
                {
                    ProcessKeyDown(vk, kb.scanCode);
                }
            }
        }

        return CallNextHookEx(_hookHandle, nCode, wParam, lParam);
    }

    // -- Procesare taste (identic Python: _on_key_press) -------------------

    /// <summary>
    /// Logica identica Python _on_key_press:
    ///   1. Daca char printabil ?i fara modificatori Ctrl/Alt ? TYPE step
    ///   2. Altfel ? KEY step cu combo (Ctrl+X, Shift+F1 etc.)
    /// </summary>
    private void ProcessKeyDown(int vk, uint scanCode)
    {
        bool hasCtrl = HasModifier(VK_LCONTROL, VK_RCONTROL);
        bool hasAlt = HasModifier(VK_LMENU, VK_RMENU);
        bool hasShift = HasModifier(VK_LSHIFT, VK_RSHIFT);
        bool hasWin = HasModifier(VK_LWIN, VK_RWIN);

        // �ncearca sa ob?ina caracterul printabil
        string? printableChar = GetPrintableChar(vk, scanCode);

        double elapsed = GetElapsed();

        // Daca char printabil ?i fara Ctrl/Alt ? TYPE step (identic Python)
        if (printableChar != null && !hasCtrl && !hasAlt && !hasWin)
        {
            var step = new StepModel
            {
                StepType = "TYPE",
                TextInput = printableChar,
                DelayBefore = elapsed,
                Description = $"Scriere: {printableChar}",
                Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
            };
            StepRecorded?.Invoke(step);
            return;
        }

        // KEY step � construie?te combo (identic Python)
        string keyName = GetKeyName(vk);
        string combo = BuildCombo(hasCtrl, hasShift, hasAlt, hasWin, keyName);

        var keyStep = new StepModel
        {
            StepType = "KEY",
            KeyCombo = combo,
            DelayBefore = elapsed,
            Description = $"Tasta: {combo}",
            Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
        };
        StepRecorded?.Invoke(keyStep);
    }

    // -- Helpers -----------------------------------------------------------

    private bool HasModifier(int vkLeft, int vkRight)
    {
        lock (_modLock)
            return _activeModifiers.Contains(vkLeft) || _activeModifiers.Contains(vkRight);
    }

    /// <summary>
    /// Ob?ine caracterul printabil pentru un VK code.
    /// Returneaza null daca nu e printabil sau e caracter de control.
    /// </summary>
    private static string? GetPrintableChar(int vk, uint scanCode)
    {
        var keyState = new byte[256];
        GetKeyboardState(keyState);

        var sb = new StringBuilder(4);
        int result = ToUnicode((uint)vk, scanCode, keyState, sb, sb.Capacity, 0);

        if (result == 1)
        {
            char c = sb[0];
            if (char.IsControl(c)) return null;
            if (char.IsWhiteSpace(c) && c != ' ') return null;
            return c.ToString();
        }
        return null;
    }

    /// <summary>
    /// Mapeaza VK code la nume de tasta (identic Python key name mapping).
    /// </summary>
    private static string GetKeyName(int vk) => vk switch
    {
        0x08 => "backspace",
        0x09 => "tab",
        0x0D => "enter",
        0x1B => "escape",
        0x20 => "space",
        0x21 => "pageup",
        0x22 => "pagedown",
        0x23 => "end",
        0x24 => "home",
        0x25 => "left",
        0x26 => "up",
        0x27 => "right",
        0x28 => "down",
        0x2C => "printscreen",
        0x2D => "insert",
        0x2E => "delete",
        0x70 => "f1",
        0x71 => "f2",
        0x72 => "f3",
        0x73 => "f4",
        0x74 => "f5",
        0x75 => "f6",
        0x76 => "f7",
        0x77 => "f8",
        0x78 => "f9",
        0x79 => "f10",
        0x7A => "f11",
        0x7B => "f12",
        0x90 => "numlock",
        0x14 => "capslock",
        0x91 => "scrolllock",
        0xA4 => "alt",
        0xA5 => "alt",
        _ => ((char)vk).ToString().ToLower()
    };

    /// <summary>
    /// Construie?te combo string (identic Python: "Ctrl+Shift+X").
    /// </summary>
    private static string BuildCombo(bool ctrl, bool shift, bool alt, bool win, string key)
    {
        var parts = new List<string>();
        if (ctrl) parts.Add("Ctrl");
        if (shift) parts.Add("Shift");
        if (alt) parts.Add("Alt");
        if (win) parts.Add("Win");
        parts.Add(key);
        return string.Join("+", parts);
    }

    private double GetElapsed()
    {
        var now = DateTime.UtcNow;
        double secs = (now - _lastTime).TotalSeconds;
        _lastTime = now;
        return Math.Min(secs, 10.0);
    }

    public void Dispose()
    {
        Stop();
    }
}