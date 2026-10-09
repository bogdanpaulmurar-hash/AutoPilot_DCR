// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// MouseRecorder.cs � WH_MOUSE_LL low-level hook
// Echivalent Python: MouseRecorderMixin (_on_move, _on_click, _on_scroll)
// ============================================================

using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Recording;

/// <summary>
/// �nregistreaza evenimentele mouse globale via WH_MOUSE_LL.
/// Ruleaza pe un thread dedicat cu propriul message loop (Application.Run).
/// Echivalent Python: MouseRecorderMixin + pynput.mouse.Listener
/// </summary>
public sealed class MouseRecorder : IDisposable
{
    // -- Win32 ------------------------------------------------------------
    private const int WH_MOUSE_LL = 14;
    private const int WM_LBUTTONDOWN = 0x0201;
    private const int WM_RBUTTONDOWN = 0x0204;
    private const int WM_MBUTTONDOWN = 0x0207;
    private const int WM_MOUSEMOVE = 0x0200;
    private const int WM_MOUSEWHEEL = 0x020A;

    [StructLayout(LayoutKind.Sequential)]
    private struct MSLLHOOKSTRUCT
    {
        public int pt_x;
        public int pt_y;
        public uint mouseData;
        public uint flags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    private delegate IntPtr LowLevelMouseProc(int nCode, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelMouseProc lpfn,
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
    private LowLevelMouseProc? _hookProc;   // keep-alive: GC nu colecteze delegate-ul
    private Thread? _hookThread;
    private volatile bool _running;

    // Stare mouse (identic Python: _last_pos, _last_time)
    private (int X, int Y) _lastPos;
    private DateTime _lastTime = DateTime.UtcNow;

    // Setari recorder (injectate din RecorderEngine)
    private volatile bool _isRecording;
    private volatile bool _isPaused;
    private bool _recordMouseMove;
    private int _mouseMoveThreshold; // px, default 5

    // -- Events (echivalent Python callbacks) ------------------------------
    /// <summary>Emis c�nd un pas nou a fost �nregistrat.</summary>
    public event Action<StepModel>? StepRecorded;

    // -- API publica -------------------------------------------------------

    /// <summary>
    /// Porne?te hook-ul mouse. Trebuie apelat o singura data.
    /// recordMouseMove ?i threshold sunt citite din AppSettings.
    /// </summary>
    public void Start(bool recordMouseMove, int mouseMoveThreshold)
    {
        if (_running) return;

        _recordMouseMove = recordMouseMove;
        _mouseMoveThreshold = mouseMoveThreshold;
        _running = true;
        _lastTime = DateTime.UtcNow;

        // Thread dedicat cu message loop � obligatoriu pentru WH_MOUSE_LL
        _hookThread = new Thread(HookThreadProc)
        {
            IsBackground = true,
            Name = "MouseHookThread"
        };
        _hookThread.Start();
    }

    /// <summary>Opre?te hook-ul ?i elibereaza resursele.</summary>
    public void Stop()
    {
        _running = false;
        // Trimite WM_QUIT pe thread-ul hook-ului pentru a ie?i din GetMessage
        if (_hookThread is { IsAlive: true })
        {
            // PostThreadMessage nu e disponibil direct � folosim Abort-safe approach
            // prin dezinstalarea hook-ului, care va cauza GetMessage sa returneze false
            if (_hookHandle != IntPtr.Zero)
            {
                UnhookWindowsHookEx(_hookHandle);
                _hookHandle = IntPtr.Zero;
            }
            _hookThread.Join(2000);
        }
    }

    /// <summary>Seteaza starea de �nregistrare (activ/pauza).</summary>
    public void SetState(bool isRecording, bool isPaused)
    {
        _isRecording = isRecording;
        _isPaused = isPaused;
    }

    /// <summary>Actualizeaza setarile (record_mouse_move, threshold) la runtime.</summary>
    public void UpdateSettings(bool recordMouseMove, int mouseMoveThreshold)
    {
        _recordMouseMove = recordMouseMove;
        _mouseMoveThreshold = mouseMoveThreshold;
    }

    // -- Thread hook -------------------------------------------------------

    private void HookThreadProc()
    {
        using var curProcess = Process.GetCurrentProcess();
        using var curModule = curProcess.MainModule!;

        _hookProc = HookCallback;
        _hookHandle = SetWindowsHookEx(
            WH_MOUSE_LL,
            _hookProc,
            GetModuleHandle(curModule.ModuleName!),
            0);

        if (_hookHandle == IntPtr.Zero)
        {
            Debug.WriteLine($"[MouseRecorder] SetWindowsHookEx e?uat: {Marshal.GetLastWin32Error()}");
            return;
        }

        // Message loop � obligatoriu pentru low-level hooks
        while (_running && GetMessage(out MSG msg, IntPtr.Zero, 0, 0))
        {
            TranslateMessage(ref msg);
            DispatchMessage(ref msg);
        }

        // Cleanup
        if (_hookHandle != IntPtr.Zero)
        {
            UnhookWindowsHookEx(_hookHandle);
            _hookHandle = IntPtr.Zero;
        }
    }

    // -- Hook callback -----------------------------------------------------

    private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0 && _isRecording && !_isPaused)
        {
            var hookStruct = Marshal.PtrToStructure<MSLLHOOKSTRUCT>(lParam);
            int x = hookStruct.pt_x;
            int y = hookStruct.pt_y;
            int msg = wParam.ToInt32();

            switch (msg)
            {
                case WM_LBUTTONDOWN:
                    OnClick(x, y, "left");
                    break;

                case WM_RBUTTONDOWN:
                    OnClick(x, y, "right");
                    break;

                case WM_MBUTTONDOWN:
                    OnClick(x, y, "middle");
                    break;

                case WM_MOUSEMOVE:
                    OnMove(x, y);
                    break;

                case WM_MOUSEWHEEL:
                    // mouseData high-word = delta (pozitiv = sus, negativ = jos)
                    short delta = (short)(hookStruct.mouseData >> 16);
                    int dy = delta / 120; // normalizat ca pynput
                    OnScroll(x, y, 0, dy);
                    break;
            }
        }

        return CallNextHookEx(_hookHandle, nCode, wParam, lParam);
    }

    // -- Handlers (identic Python: _on_click, _on_move, _on_scroll) --------

    /// <summary>
    /// Echivalent Python: _on_click(x, y, button, pressed)
    /// �nregistreaza CLICK sau RIGHTCLICK (doar la press, nu release).
    /// </summary>
    private void OnClick(int x, int y, string button)
    {
        string stepType = button == "right" ? "RIGHTCLICK" : "CLICK";
        string clickType = button == "right" ? "right" : "single";

        _lastPos = (x, y);
        double elapsed = GetElapsed();

        var step = new StepModel
        {
            StepType = stepType,
            X = x,
            Y = y,
            Button = button,
            ClickType = clickType,
            DelayBefore = elapsed,
            Description = $"Click {button} la ({x}, {y})",
            Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
        };

        StepRecorded?.Invoke(step);
    }

    /// <summary>
    /// Echivalent Python: _on_move(x, y)
    /// �nregistreaza MOVE doar daca record_mouse_move=true ?i distan?a >= threshold.
    /// Distan?a Euclidiana (identic Python).
    /// </summary>
    private void OnMove(int x, int y)
    {
        if (!_recordMouseMove) return;

        // Distan?a Euclidiana fa?a de ultima pozi?ie
        double dx = x - _lastPos.X;
        double dy = y - _lastPos.Y;
        double dist = Math.Sqrt(dx * dx + dy * dy);

        if (dist < _mouseMoveThreshold) return;

        _lastPos = (x, y);
        double elapsed = GetElapsed();

        var step = new StepModel
        {
            StepType = "MOVE",
            X = x,
            Y = y,
            DelayBefore = elapsed,
            Description = $"Move la ({x}, {y})",
            Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
        };

        StepRecorded?.Invoke(step);
    }

    /// <summary>
    /// Echivalent Python: _on_scroll(x, y, dx, dy)
    /// </summary>
    private void OnScroll(int x, int y, int dx, int dy)
    {
        double elapsed = GetElapsed();

        var step = new StepModel
        {
            StepType = "SCROLL",
            X = x,
            Y = y,
            ScrollDx = dx,
            ScrollDy = dy,
            DelayBefore = elapsed,
            Description = $"Scroll ({dx},{dy}) la ({x},{y})",
            Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
        };

        StepRecorded?.Invoke(step);
    }

    // -- Helpers -----------------------------------------------------------

    /// <summary>
    /// Calculeaza timpul scurs de la ultimul eveniment (cap la 10.0s).
    /// Identic Python: _elapsed() ? float (capped at 10.0s)
    /// </summary>
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