// ============================================================
// AutoPilot DC v4.1
// ScreenProbe.cs — Ce e pe ecran: fereastra de la un punct, fereastra activa,
// amprenta zonei din jurul unui click, ferestre de eroare, aplicatii blocate.
//
// Amprenta (semnatura) e identica cu versiunea Python, ca rutinele sa fie compatibile:
//   zona 40x40 px centrata pe click -> tonuri de gri (299R+587G+114B)/1000
//   -> medie pe blocuri 2x2 -> 20x20 octeti -> base64.
// ============================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace AutoPilotDC.Infrastructure.Safety;

/// <summary>O fereastra de nivel superior.</summary>
public sealed record WindowInfo(IntPtr Handle, string Title, string ClassName, string Process, int ProcessId)
{
    public static readonly WindowInfo None = new(IntPtr.Zero, "", "", "", 0);

    public bool IsDialog => ClassName == "#32770";

    public override string ToString() =>
        string.IsNullOrEmpty(Title) ? $"[{Process}]" : $"\"{Title}\" ({Process})";
}

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public static class ScreenProbe
{
    public const int PatchSize = 40;   // zona capturata (px)
    public const int SignatureSize = 20;

    private static readonly int OwnPid = Environment.ProcessId;

    /// <summary>true daca fereastra apartine aplicatiei AutoPilot (dialoguri, chenar, bara de control).</summary>
    public static bool IsOwn(WindowInfo w) => w.ProcessId == OwnPid;

    // =========================================================
    // Ferestre
    // =========================================================

    /// <summary>Fereastra principala (radacina) aflata sub punctul (x, y).</summary>
    public static WindowInfo WindowAt(int x, int y)
    {
        var h = WindowFromPoint(new POINT { X = x, Y = y });
        if (h == IntPtr.Zero) return WindowInfo.None;
        var root = GetAncestor(h, GA_ROOT);
        return Describe(root == IntPtr.Zero ? h : root);
    }

    /// <summary>Fereastra activa (in care ajung tastele).</summary>
    public static WindowInfo Foreground() => Describe(GetForegroundWindow());

    public static WindowInfo Describe(IntPtr hwnd)
    {
        if (hwnd == IntPtr.Zero) return WindowInfo.None;
        var title = new StringBuilder(512);
        GetWindowText(hwnd, title, title.Capacity);
        var cls = new StringBuilder(256);
        GetClassName(hwnd, cls, cls.Capacity);
        GetWindowThreadProcessId(hwnd, out uint pid);
        return new WindowInfo(hwnd, title.ToString(), cls.ToString(), ProcessName(pid), (int)pid);
    }

    /// <summary>Ferestrele vizibile de nivel superior (cu titlu sau dialoguri).</summary>
    public static List<WindowInfo> TopLevelWindows()
    {
        var list = new List<WindowInfo>();
        EnumWindows((h, _) =>
        {
            if (!IsWindowVisible(h)) return true;
            long ex = GetWindowLongPtr(h, GWL_EXSTYLE).ToInt64();
            if ((ex & WS_EX_TOOLWINDOW) != 0) return true;
            var w = Describe(h);
            if (w.Title.Length > 0 || w.IsDialog) list.Add(w);
            return true;
        }, IntPtr.Zero);
        return list;
    }

    /// <summary>Textul dintr-un dialog standard (mesajul erorii), din controalele Static.</summary>
    public static string DialogText(IntPtr hwnd)
    {
        var sb = new StringBuilder();
        EnumChildWindows(hwnd, (h, _) =>
        {
            var cls = new StringBuilder(64);
            GetClassName(h, cls, cls.Capacity);
            if (cls.ToString() is "Static" or "DirectUIHWND" && IsWindowVisible(h))
            {
                var t = new StringBuilder(1024);
                GetWindowText(h, t, t.Capacity);
                var text = t.ToString().Trim();
                if (text.Length > 0) sb.AppendLine(text);
            }
            return sb.Length < 1500;
        }, IntPtr.Zero);
        return sb.ToString().Trim();
    }

    /// <summary>Aplicatia nu raspunde (Windows o considera "Not Responding").</summary>
    public static bool IsHung(IntPtr hwnd) => hwnd != IntPtr.Zero && IsHungAppWindow(hwnd);

    // ── Cuvinte care indica o eroare in titlul / textul unei ferestre ──
    private static readonly string[] ErrorWords =
    {
        "error", "eroare", "erori", "fehler", "exception", "exceptie", "excepție",
        "warning", "avertisment", "atentie", "atenție", "failed", "esuat", "eșuat",
        "not responding", "nu raspunde", "nu răspunde", "problem", "problema", "problemă",
        "fatal", "crash", "access denied", "acces refuzat",
    };

    public static bool LooksLikeError(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return false;
        var lower = text.ToLowerInvariant();
        foreach (var w in ErrorWords)
            if (lower.Contains(w)) return true;
        return false;
    }

    // =========================================================
    // Cursor
    // =========================================================
    public static (int X, int Y) CursorPosition()
    {
        GetCursorPos(out var p);
        return (p.X, p.Y);
    }

    public static void MoveCursor(int x, int y) => SetCursorPos(x, y);

    // =========================================================
    // Amprenta zonei din jurul unui punct
    // =========================================================

    /// <summary>Captureaza amprenta zonei centrate pe (x, y). Null daca nu se poate captura.</summary>
    public static string? CaptureSignature(int x, int y)
    {
        try
        {
            // zona e mutata in interiorul ecranului virtual (click langa margine)
            int vx = GetSystemMetrics(SM_XVIRTUALSCREEN), vy = GetSystemMetrics(SM_YVIRTUALSCREEN);
            int vw = GetSystemMetrics(SM_CXVIRTUALSCREEN), vh = GetSystemMetrics(SM_CYVIRTUALSCREEN);
            int left = Math.Clamp(x - PatchSize / 2, vx, Math.Max(vx, vx + vw - PatchSize));
            int top = Math.Clamp(y - PatchSize / 2, vy, Math.Max(vy, vy + vh - PatchSize));

            using var bmp = new Bitmap(PatchSize, PatchSize, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(bmp))
                g.CopyFromScreen(left, top, 0, 0, new Size(PatchSize, PatchSize), CopyPixelOperation.SourceCopy);

            var data = bmp.LockBits(new Rectangle(0, 0, PatchSize, PatchSize), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            var raw = new byte[data.Stride * PatchSize];
            Marshal.Copy(data.Scan0, raw, 0, raw.Length);
            int stride = data.Stride;
            bmp.UnlockBits(data);

            var gray = new int[PatchSize * PatchSize];
            for (int py = 0; py < PatchSize; py++)
                for (int px = 0; px < PatchSize; px++)
                {
                    int i = py * stride + px * 4; // BGRA
                    gray[py * PatchSize + px] = (raw[i + 2] * 299 + raw[i + 1] * 587 + raw[i] * 114) / 1000;
                }

            var sig = new byte[SignatureSize * SignatureSize];
            for (int sy = 0; sy < SignatureSize; sy++)
                for (int sx = 0; sx < SignatureSize; sx++)
                {
                    int a = gray[(sy * 2) * PatchSize + sx * 2], b = gray[(sy * 2) * PatchSize + sx * 2 + 1];
                    int c = gray[(sy * 2 + 1) * PatchSize + sx * 2], d = gray[(sy * 2 + 1) * PatchSize + sx * 2 + 1];
                    sig[sy * SignatureSize + sx] = (byte)((a + b + c + d + 2) / 4);
                }
            return Convert.ToBase64String(sig);
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Cat de diferite sunt doua amprente: 0 = identice, 100 = complet diferite. Null = nu se pot compara.</summary>
    public static double? CompareSignatures(string? a, string? b)
    {
        if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b)) return null;
        try
        {
            var x = Convert.FromBase64String(a);
            var y = Convert.FromBase64String(b);
            if (x.Length != y.Length || x.Length == 0) return null;
            long sum = 0;
            for (int i = 0; i < x.Length; i++) sum += Math.Abs(x[i] - y[i]);
            return sum * 100.0 / (x.Length * 255.0);
        }
        catch
        {
            return null;
        }
    }

    // =========================================================
    // Procese
    // =========================================================
    private static readonly Dictionary<uint, string> ProcessNames = new();

    private static string ProcessName(uint pid)
    {
        lock (ProcessNames)
            if (ProcessNames.TryGetValue(pid, out var cached)) return cached;

        string name = "";
        IntPtr h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
        if (h != IntPtr.Zero)
        {
            try
            {
                var sb = new StringBuilder(1024);
                int size = sb.Capacity;
                if (QueryFullProcessImageName(h, 0, sb, ref size))
                    name = Path.GetFileName(sb.ToString()).ToLowerInvariant();
            }
            finally
            {
                CloseHandle(h);
            }
        }
        lock (ProcessNames)
        {
            if (ProcessNames.Count > 500) ProcessNames.Clear();
            ProcessNames[pid] = name;
        }
        return name;
    }

    // =========================================================
    // Excludere din capturi de ecran (chenarul RUN/REC nu apare in amprente)
    // =========================================================

    /// <summary>Fereastra nu mai apare in capturile de ecran (Windows 10 2004+). False daca nu e suportat.</summary>
    public static bool ExcludeFromCapture(IntPtr hwnd) => SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);

    /// <summary>Fereastra lasa click-urile sa treaca prin ea, nu primeste focus si nu apare in Alt+Tab.</summary>
    public static void MakeClickThrough(IntPtr hwnd)
    {
        long ex = GetWindowLongPtr(hwnd, GWL_EXSTYLE).ToInt64();
        ex |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW;
        SetWindowLongPtr(hwnd, GWL_EXSTYLE, new IntPtr(ex));
    }

    /// <summary>Pozitioneaza fereastra in pixeli fizici, deasupra tuturor, fara sa o activeze.</summary>
    public static void PlaceTopmost(IntPtr hwnd, int x, int y, int w, int h) =>
        SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW);

    // =========================================================
    // P/Invoke
    // =========================================================
    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    private delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);

    private const uint GA_ROOT = 2;
    private const int GWL_EXSTYLE = -20;
    private const long WS_EX_TRANSPARENT = 0x00000020;
    private const long WS_EX_TOOLWINDOW = 0x00000080;
    private const long WS_EX_LAYERED = 0x00080000;
    private const long WS_EX_NOACTIVATE = 0x08000000;
    private const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011;
    private const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
    private const int SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77, SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79;
    private static readonly IntPtr HWND_TOPMOST = new(-1);
    private const uint SWP_NOACTIVATE = 0x0010, SWP_SHOWWINDOW = 0x0040;

    [DllImport("user32.dll")] private static extern IntPtr WindowFromPoint(POINT p);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr hwnd, StringBuilder name, int max);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lParam);
    [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumWindowsProc cb, IntPtr lParam);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool IsHungAppWindow(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] private static extern int GetSystemMetrics(int index);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLongPtr(IntPtr hwnd, int index);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern IntPtr SetWindowLongPtr(IntPtr hwnd, int index, IntPtr value);
    [DllImport("user32.dll")] private static extern bool SetWindowDisplayAffinity(IntPtr hwnd, uint affinity);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr hwnd, IntPtr after, int x, int y, int w, int h, uint flags);
    [DllImport("kernel32.dll")] private static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, EntryPoint = "QueryFullProcessImageNameW")]
    private static extern bool QueryFullProcessImageName(IntPtr process, int flags, StringBuilder name, ref int size);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
}
