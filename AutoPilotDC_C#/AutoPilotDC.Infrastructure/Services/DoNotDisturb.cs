// ============================================================
// AutoPilot DC v4.1
// DoNotDisturb.cs — "Nu deranja" (Focus Assist) pe durata rularii
//
// De ce asa: Windows nu are un API public pentru "Nu deranja".
//   - Scrierea directa a starii WNF NU blocheaza notificarile (testat pe Win10 22H2).
//   - Metoda care functioneaza (aceeasi ca setarea din Windows):
//       1. profilul "Microsoft.QuietHoursProfile.PriorityOnly" se scrie in
//          HKCU\...\CloudStore\...\quiethourssettings\Current\Data
//       2. serviciul de notificari al utilizatorului (WpnUserService_xxxx)
//          se reporneste ca sa citeasca noua valoare. Nu cere drepturi de admin.
//   - Starea efectiva se verifica prin WNF (WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED).
//
// Siguranta: inainte de activare se scrie %LOCALAPPDATA%\AutoPilotDC\dnd_restore.json.
// Daca aplicatia se inchide fortat, la urmatoarea pornire RecoverIfNeeded()
// readuce notificarile (fisierul e comun cu versiunea Python).
// ============================================================

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using Microsoft.Win32;

namespace AutoPilotDC.Infrastructure.Services;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public static class DoNotDisturb
{
    private const string CloudStoreBase = @"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current";
    private const string ProfilePrefix = "Microsoft.QuietHoursProfile.";
    private const string ProfileOn = ProfilePrefix + "PriorityOnly";
    private const string ProfileOff = ProfilePrefix + "Unrestricted";

    private static readonly object Lock = new();
    private static int _users;              // rulare + inregistrare pot cere DND in acelasi timp
    private static List<string>? _changed;  // cheile pe care le-am modificat noi

    /// <summary>Ultimul mesaj (pentru bara de stare / log).</summary>
    public static string LastMessage { get; private set; } = "";

    public static string RecoveryFile => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AutoPilotDC", "dnd_restore.json");

    // =========================================================
    // API
    // =========================================================

    /// <summary>
    /// Activeaza "Nu deranja". Poate dura cateva secunde (repornirea serviciului) —
    /// apeleaz-o de pe un fir de fundal. Returneaza true daca notificarile sunt blocate.
    /// </summary>
    public static bool Enable()
    {
        lock (Lock)
        {
            _users++;
            if (_users > 1) return IsActive() != false;

            try
            {
                var targets = Discover();
                if (targets.Count == 0)
                {
                    LastMessage = "Nu deranja: setarea Windows nu a fost gasita (versiune Windows necunoscuta).";
                    return false;
                }

                // Deja activ (pornit de utilizator) -> nu atingem nimic si nu il oprim la final
                if (targets.All(t => !string.Equals(ReadProfile(t.Data), ProfileOff, StringComparison.Ordinal)))
                {
                    _changed = null;
                    LastMessage = "Nu deranja era deja activ.";
                    return true;
                }

                var changed = new List<string>();
                SaveRecovery(targets.Select(t => t.Path).ToList());
                foreach (var t in targets)
                {
                    var blob = WriteProfile(t.Data, ProfileOn);
                    if (blob != null && WriteBlob(t.Path, blob)) changed.Add(t.Path);
                }
                if (changed.Count == 0)
                {
                    DeleteRecovery();
                    LastMessage = "Nu deranja: setarea Windows nu a putut fi scrisa.";
                    return false;
                }

                _changed = changed;
                SaveRecovery(changed);
                RestartNotificationService();
                bool ok = WaitForState(on: true);
                LastMessage = ok ? "🌙 Nu deranja activ — notificarile sunt oprite pe durata rularii."
                                 : "Nu deranja a fost setat, dar Windows nu a confirmat inca.";
                return ok;
            }
            catch (Exception ex)
            {
                LastMessage = "Nu deranja nu a putut fi activat: " + ex.Message;
                return false;
            }
        }
    }

    /// <summary>Reda notificarile (doar daca noi le-am oprit). Sigur de apelat de mai multe ori.</summary>
    public static void Restore()
    {
        lock (Lock)
        {
            if (_users == 0) return;
            _users--;
            if (_users > 0) return;

            var changed = _changed;
            _changed = null;
            if (changed == null) return;
            RestoreKeys(changed);
        }
    }

    /// <summary>La inchiderea aplicatiei: reda notificarile chiar daca o rulare nu s-a terminat.</summary>
    public static void RestoreAll()
    {
        lock (Lock)
        {
            if (_users == 0) return;
            _users = 1;
            Restore();
        }
    }

    /// <summary>La pornirea aplicatiei: daca o rulare anterioara a ramas cu "Nu deranja" pornit, il oprim.</summary>
    public static void RecoverIfNeeded()
    {
        try
        {
            if (!File.Exists(RecoveryFile)) return;
            var keys = JsonSerializer.Deserialize<List<string>>(File.ReadAllText(RecoveryFile)) ?? new();
            lock (Lock) RestoreKeys(keys);
        }
        catch
        {
            // fisier corupt: il stergem ca sa nu incercam la nesfarsit
            DeleteRecovery();
        }
    }

    /// <summary>Starea efectiva in Windows: true = notificari blocate, false = libere, null = necunoscut.</summary>
    public static bool? IsActive()
    {
        try
        {
            ulong name = 0x0D83063EA3BF1C75; // WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED
            var buf = new byte[16];
            uint size = (uint)buf.Length;
            int status = NtQueryWnfStateData(ref name, IntPtr.Zero, IntPtr.Zero, out _, buf, ref size);
            if (status != 0 || size < 4) return null;
            return BitConverter.ToInt32(buf, 0) != 0; // 0 = oprit, 1 = prioritare, 2 = doar alarme
        }
        catch
        {
            return null;
        }
    }

    // =========================================================
    // CloudStore (registry)
    // =========================================================
    private sealed record Target(string Path, byte[] Data);

    /// <summary>
    /// Cheia are nume diferite intre versiuni (…notifications.quiethourssettings /
    /// …donotdisturb.quiethourssettings) si pot exista mai multe containere -> le cautam pe toate.
    /// </summary>
    private static List<Target> Discover()
    {
        var list = new List<Target>();
        using var root = Registry.CurrentUser.OpenSubKey(CloudStoreBase);
        if (root == null) return list;

        foreach (var name in root.GetSubKeyNames())
        {
            if (!name.Contains("quiethourssettings", StringComparison.OrdinalIgnoreCase)) continue;
            using var container = root.OpenSubKey(name);
            if (container == null) continue;
            foreach (var child in container.GetSubKeyNames())
            {
                var path = $@"{CloudStoreBase}\{name}\{child}";
                using var key = Registry.CurrentUser.OpenSubKey(path);
                if (key?.GetValue("Data") is byte[] data && ReadProfile(data) != null)
                    list.Add(new Target(path, data));
            }
        }
        return list;
    }

    /// <summary>Numele profilului din blob (sir UTF-16 precedat de numarul de caractere).</summary>
    internal static string? ReadProfile(byte[] blob)
    {
        int idx = FindPrefix(blob);
        if (idx < 1) return null;
        int chars = blob[idx - 1];
        if (idx + chars * 2 > blob.Length) return null;
        return Encoding.Unicode.GetString(blob, idx, chars * 2);
    }

    /// <summary>
    /// Inlocuieste numele profilului (doar daca are aceeasi lungime — Unrestricted si
    /// PriorityOnly au amandoua 40 de caractere) si actualizeaza marca de timp.
    /// </summary>
    internal static byte[]? WriteProfile(byte[] blob, string profile)
    {
        int idx = FindPrefix(blob);
        if (idx < 1) return null;
        int chars = blob[idx - 1];
        if (chars != profile.Length || idx + chars * 2 > blob.Length) return null;

        var copy = (byte[])blob.Clone();
        Encoding.Unicode.GetBytes(profile, 0, profile.Length, copy, idx);

        // Marca de timp: tag 2a 06 la offset 8, 5 octeti LEB128 (secunde Unix) de la offset 10.
        // O marca veche face ca Explorer sa pastreze valoarea din cache.
        if (copy.Length > 15 && copy[8] == 0x2a && copy[9] == 0x06)
        {
            ulong t = (ulong)DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            for (int k = 0; k < 5; k++)
            {
                byte b = (byte)(t & 0x7f);
                t >>= 7;
                if (k < 4) b |= 0x80;
                copy[10 + k] = b;
            }
        }
        return copy;
    }

    private static int FindPrefix(byte[] blob)
    {
        var p = Encoding.Unicode.GetBytes(ProfilePrefix);
        for (int i = 0; i <= blob.Length - p.Length; i++)
        {
            int j = 0;
            while (j < p.Length && blob[i + j] == p[j]) j++;
            if (j == p.Length) return i;
        }
        return -1;
    }

    private static bool WriteBlob(string path, byte[] data)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(path, writable: true);
            if (key == null) return false;
            key.SetValue("Data", data, RegistryValueKind.Binary);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static void RestoreKeys(List<string> keys)
    {
        foreach (var path in keys)
        {
            try
            {
                using var key = Registry.CurrentUser.OpenSubKey(path);
                if (key?.GetValue("Data") is not byte[] data) continue;
                // Oprim doar daca e inca profilul pus de noi (utilizatorul poate sa-l fi schimbat)
                if (!string.Equals(ReadProfile(data), ProfileOn, StringComparison.Ordinal)) continue;
                var blob = WriteProfile(data, ProfileOff);
                if (blob != null) WriteBlob(path, blob);
            }
            catch { /* best effort */ }
        }
        RestartNotificationService();
        WaitForState(on: false);
        DeleteRecovery();
        LastMessage = "Notificarile Windows au fost repornite.";
    }

    private static bool WaitForState(bool on)
    {
        for (int i = 0; i < 25; i++)
        {
            if (IsActive() == on) return true;
            Thread.Sleep(200);
        }
        return false;
    }

    private static void SaveRecovery(List<string> keys)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(RecoveryFile)!);
            File.WriteAllText(RecoveryFile, JsonSerializer.Serialize(keys));
        }
        catch { }
    }

    private static void DeleteRecovery()
    {
        try { if (File.Exists(RecoveryFile)) File.Delete(RecoveryFile); } catch { }
    }

    // =========================================================
    // Serviciul de notificari al utilizatorului (WpnUserService_xxxx)
    // =========================================================
    private static void RestartNotificationService()
    {
        IEnumerable<string> names;
        try
        {
            using var services = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services");
            names = services?.GetSubKeyNames()
                        .Where(n => n.StartsWith("WpnUserService_", StringComparison.OrdinalIgnoreCase))
                        .ToList() ?? new List<string>();
        }
        catch
        {
            return;
        }

        IntPtr scm = OpenSCManager(null, null, SC_MANAGER_CONNECT);
        if (scm == IntPtr.Zero) return;
        try
        {
            foreach (var name in names)
            {
                // Instantele altor sesiuni nu se pot deschide -> sunt ignorate
                IntPtr svc = OpenService(scm, name, SERVICE_START | SERVICE_STOP | SERVICE_QUERY_STATUS);
                if (svc == IntPtr.Zero) continue;
                try
                {
                    if (!QueryServiceStatus(svc, out var st) || st.dwCurrentState != SERVICE_RUNNING) continue;
                    ControlService(svc, SERVICE_CONTROL_STOP, out _);
                    WaitServiceState(svc, SERVICE_STOPPED);
                    // Pornim mereu la loc: un serviciu de notificari oprit e mai rau decat un DND neaplicat
                    for (int i = 0; i < 20; i++)
                    {
                        if (StartService(svc, 0, null)) break;
                        Thread.Sleep(100);
                    }
                    WaitServiceState(svc, SERVICE_RUNNING);
                }
                finally
                {
                    CloseServiceHandle(svc);
                }
            }
        }
        finally
        {
            CloseServiceHandle(scm);
        }
    }

    private static void WaitServiceState(IntPtr svc, uint state)
    {
        for (int i = 0; i < 50; i++)
        {
            if (QueryServiceStatus(svc, out var st) && st.dwCurrentState == state) return;
            Thread.Sleep(100);
        }
    }

    // =========================================================
    // P/Invoke
    // =========================================================
    private const uint SC_MANAGER_CONNECT = 0x0001;
    private const uint SERVICE_QUERY_STATUS = 0x0004;
    private const uint SERVICE_START = 0x0010;
    private const uint SERVICE_STOP = 0x0020;
    private const uint SERVICE_CONTROL_STOP = 0x00000001;
    private const uint SERVICE_STOPPED = 0x00000001;
    private const uint SERVICE_RUNNING = 0x00000004;

    [StructLayout(LayoutKind.Sequential)]
    private struct SERVICE_STATUS
    {
        public uint dwServiceType, dwCurrentState, dwControlsAccepted, dwWin32ExitCode,
                    dwServiceSpecificExitCode, dwCheckPoint, dwWaitHint;
    }

    [DllImport("advapi32.dll", EntryPoint = "OpenSCManagerW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr OpenSCManager(string? machine, string? database, uint access);

    [DllImport("advapi32.dll", EntryPoint = "OpenServiceW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr OpenService(IntPtr scm, string name, uint access);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool ControlService(IntPtr svc, uint control, out SERVICE_STATUS status);

    [DllImport("advapi32.dll", EntryPoint = "StartServiceW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool StartService(IntPtr svc, uint argc, string[]? argv);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool QueryServiceStatus(IntPtr svc, out SERVICE_STATUS status);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool CloseServiceHandle(IntPtr handle);

    [DllImport("ntdll.dll")]
    private static extern int NtQueryWnfStateData(ref ulong stateName, IntPtr typeId, IntPtr explicitScope,
                                                  out uint changeStamp, byte[] buffer, ref uint bufferSize);
}
