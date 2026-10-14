// ============================================================
// AutoPilot DC v4 — Drivers.Windows
// Win32.cs — Functii Windows folosite de Spy (cursor, taste)
// + StaWorker: un fir STA dedicat pentru obiectele COM (SAP GUI).
// ============================================================

using System.Collections.Concurrent;
using System.Runtime.InteropServices;

namespace AutoPilotDC.Drivers.Windows;

internal static class Win32
{
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vKey);

    public const int VK_ESCAPE = 0x1B;
    public const int VK_F2 = 0x71;

    /// <summary>Tasta e apasata acum?</summary>
    public static bool IsDown(int vk) => (GetAsyncKeyState(vk) & 0x8000) != 0;

    /// <summary>Asteapta pana tasta e eliberata (ca sa nu capturam de doua ori).</summary>
    public static async Task WaitReleaseAsync(int vk, CancellationToken ct)
    {
        while (IsDown(vk)) await Task.Delay(30, ct);
    }
}

/// <summary>
/// Fir STA dedicat: toate apelurile COM catre SAP GUI trec prin el
/// (obiectele SAP sunt sensibile la firul de executie).
/// </summary>
internal sealed class StaWorker : IDisposable
{
    private readonly BlockingCollection<Action> _queue = new();
    private readonly Thread _thread;

    public StaWorker(string name)
    {
        _thread = new Thread(() =>
        {
            foreach (var work in _queue.GetConsumingEnumerable()) work();
        })
        { IsBackground = true, Name = name };
        _thread.SetApartmentState(ApartmentState.STA);
        _thread.Start();
    }

    public Task<T> RunAsync<T>(Func<T> func)
    {
        var tcs = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        _queue.Add(() =>
        {
            try { tcs.SetResult(func()); }
            catch (Exception ex) { tcs.SetException(ex); }
        });
        return tcs.Task;
    }

    public Task RunAsync(Action action) => RunAsync(() => { action(); return true; });

    public void Dispose() => _queue.CompleteAdding();
}
