// ============================================================
// AutoPilot DC v4 — Drivers.Windows
// SapUiDriver.cs — SAP GUI prin SAP GUI Scripting (COM)
//
// Cerinte pe PC: SAP GUI for Windows + scripting activat
//   (SAP GUI Options -> Accessibility & Scripting -> Enable scripting;
//    pe server: parametrul sapgui/user_scripting = TRUE).
// Nu are nevoie de referinte la DLL-uri SAP: se ataseaza la SAP GUI
// deschis prin Running Object Table ("SAPGUI").
//
//  - Spy: elementul SAP de sub mouse e conturat cu rosu (Visualize);
//    F2 = captureaza, Esc = anuleaza. Daca pozitia nu poate fi
//    determinata, se captureaza campul care are focusul.
//  - Locatori: Id SAP (wnd[0]/usr/ctxt...) + Nume|Tip ca rezerva.
// ============================================================

using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text.RegularExpressions;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Drivers.Windows;

public sealed class SapUiDriver : IUiDriver, ISpyCapable
{
    private readonly StaWorker _sta = new("SAP-GUI-Scripting");
    private dynamic? _session;

    public UiTechnology Technology => UiTechnology.Sap;
    public string DisplayName => "SAP GUI (Scripting)";

    // =========================================================
    // 1. Conectare la SAP GUI deschis
    // =========================================================
    [DllImport("ole32.dll")] private static extern int GetRunningObjectTable(int reserved, out IRunningObjectTable prot);
    [DllImport("ole32.dll")] private static extern int CreateBindCtx(int reserved, out IBindCtx ppbc);

    private static object GetSapGuiRotEntry()
    {
        GetRunningObjectTable(0, out var rot);
        CreateBindCtx(0, out var ctx);
        rot.EnumRunning(out var enumMoniker);
        enumMoniker.Reset();
        var monikers = new IMoniker[1];
        while (enumMoniker.Next(1, monikers, IntPtr.Zero) == 0)
        {
            monikers[0].GetDisplayName(ctx, null, out var name);
            if (name != null && name.Contains("SAPGUI", StringComparison.OrdinalIgnoreCase))
            {
                rot.GetObject(monikers[0], out var obj);
                return obj;
            }
        }
        throw new RprStepException("SAP GUI nu este deschis (sau scripting-ul este dezactivat). Deschide SAP Logon si autentifica-te.");
    }

    /// <summary>"" = prima sesiune; "2" = sesiunea 2 din prima conexiune; "1/0" = conexiunea 1, sesiunea 0.</summary>
    private void Connect(string which)
    {
        var rotEntry = GetSapGuiRotEntry();
        object engine = rotEntry.GetType().InvokeMember("GetScriptingEngine", BindingFlags.InvokeMethod, null, rotEntry, null)
                        ?? throw new RprStepException("SAP GUI Scripting nu raspunde. Verifica daca scripting-ul este activat.");
        dynamic app = engine;

        int con = 0, ses = 0;
        which = (which ?? "").Trim();
        if (which.Contains('/'))
        {
            var parts = which.Split('/');
            int.TryParse(parts[0], out con);
            int.TryParse(parts[1], out ses);
        }
        else if (which.Length > 0) int.TryParse(which, out ses);

        if ((int)app.Children.Count == 0)
            throw new RprStepException("Nu exista nicio conexiune SAP deschisa. Autentifica-te in SAP Logon.");
        dynamic connection = app.Children.Item(con);
        if ((int)connection.Children.Count <= ses)
            throw new RprStepException($"Sesiunea SAP {ses} nu exista (deschise: {(int)connection.Children.Count}).");
        _session = connection.Children.Item(ses);
    }

    private dynamic Session
    {
        get
        {
            if (_session == null) Connect("");
            try
            {
                _ = (string)_session!.Id; // sesiune inca vie?
            }
            catch (COMException)
            {
                Connect("");
            }
            return _session!;
        }
    }

    private void WaitWhileBusy(int timeoutMs)
    {
        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(1000, timeoutMs));
        while ((bool)Session.Busy)
        {
            if (DateTime.UtcNow > deadline) throw new RprStepException("SAP este ocupat (Busy) prea mult timp.");
            Thread.Sleep(100);
        }
    }

    // =========================================================
    // 2. Gasire element
    // =========================================================
    private static string RelativeId(string fullId) =>
        Regex.Replace(fullId, @"^/app/con\[\d+\]/ses\[\d+\]/", "");

    private dynamic? FindOnce(UiObject obj, out Locator? used)
    {
        used = null;
        foreach (var loc in obj.ActiveLocators)
        {
            try
            {
                dynamic? el = null;
                if (loc.Kind == LocatorKind.SapId)
                {
                    el = Session.FindById(loc.Value, false);
                }
                else if (loc.Kind == LocatorKind.SapName)
                {
                    var p = loc.Value.IndexOf('|');
                    var name = p >= 0 ? loc.Value[..p] : loc.Value;
                    var type = p >= 0 ? loc.Value[(p + 1)..] : "";
                    dynamic wnd = Session.ActiveWindow;
                    dynamic all = wnd.FindAllByName(name, type);
                    if ((int)all.Count >= 1) el = all.Item(0);
                }
                if (el != null) { used = loc; return el; }
            }
            catch (COMException) { /* locatorul nu se potriveste pe ecranul curent */ }
            catch (Microsoft.CSharp.RuntimeBinder.RuntimeBinderException) { }
        }
        return null;
    }

    private dynamic Require(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, timeoutMs));
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            WaitWhileBusy(timeoutMs);
            var el = FindOnce(obj, out _);
            if (el != null) return el;
            if (DateTime.UtcNow >= deadline)
            {
                string screen = "";
                try { screen = $"ecran curent: {(string)Session.Info.Transaction} / {(string)Session.ActiveWindow.Text}"; } catch (Exception) { }
                throw new ElementNotFoundException(obj, timeoutMs, screen);
            }
            Thread.Sleep(250);
        }
    }

    // =========================================================
    // 3. IUiDriver
    // =========================================================
    public Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct) =>
        _sta.RunAsync(() =>
        {
            var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, timeoutMs));
            while (true)
            {
                dynamic? el = null; Locator? used = null;
                try { el = FindOnce(obj, out used); } catch (RprStepException) { return ElementState.NotFound; }
                if (el != null)
                {
                    string text = SafeString(() => (string)el.Text);
                    bool changeable = SafeBool(() => (bool)el.Changeable, true);
                    return new ElementState(true, true, changeable, text, text, used);
                }
                if (DateTime.UtcNow >= deadline || ct.IsCancellationRequested) return ElementState.NotFound;
                Thread.Sleep(250);
            }
        });

    public Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct) =>
        _sta.RunAsync(() =>
        {
            try
            {
                var el = FindOnce(obj, out _);
                if (el == null) return;
                el.Visualize(true);
                Thread.Sleep(Math.Clamp(durationMs, 100, 2000));
                el.Visualize(false);
            }
            catch (Exception) { /* optional */ }
        });

    public Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct) =>
        _sta.RunAsync<string?>(() =>
        {
            try
            {
                var path = Path.Combine(folder, name + ".png");
                Session.ActiveWindow.HardCopy(path, 2); // 2 = PNG
                return path;
            }
            catch (Exception) { return null; }
        });

    public async Task<string?> ExecuteAsync(ActionRequest r, CancellationToken ct)
    {
        try
        {
            return await _sta.RunAsync(() => Execute(r, ct));
        }
        catch (COMException ex)
        {
            throw new RprStepException($"SAP: {ex.Message}", ex);
        }
        catch (Microsoft.CSharp.RuntimeBinder.RuntimeBinderException ex)
        {
            throw new RprStepException($"Actiunea {r.Action} nu e suportata de acest tip de element SAP ({ex.Message}).", ex);
        }
    }

    private string? Execute(ActionRequest r, CancellationToken ct)
    {
        // ── Fara obiect ─────────────────────────────────────
        switch (r.Action)
        {
            case RprAction.SapConnect:
                Connect(r.Value);
                return (string)_session!.Info.SystemName + " / client " + (string)_session.Info.Client;

            case RprAction.SapTransaction:
            {
                var tcode = r.Value.Trim();
                if (string.IsNullOrEmpty(tcode)) throw new RprStepException("Codul tranzactiei lipseste.");
                if (tcode.StartsWith("/n", StringComparison.OrdinalIgnoreCase) || tcode.StartsWith("/o", StringComparison.OrdinalIgnoreCase))
                {
                    Session.FindById("wnd[0]/tbar[0]/okcd").Text = tcode;
                    Session.FindById("wnd[0]").SendVKey(0);
                }
                else
                {
                    Session.StartTransaction(tcode);
                }
                WaitWhileBusy(r.TimeoutMs);
                return null;
            }

            case RprAction.SapSendKey:
            case RprAction.PressKey when r.Target == null:
                Session.ActiveWindow.SendVKey(SapVKey(r.Value));
                WaitWhileBusy(r.TimeoutMs);
                return null;

            case RprAction.SapReadStatusBar:
            {
                WaitWhileBusy(r.TimeoutMs);
                dynamic sbar = Session.FindById("wnd[0]/sbar");
                string type = SafeString(() => (string)sbar.MessageType); // S, E, W, I, A
                string text = SafeString(() => (string)sbar.Text);
                return string.IsNullOrEmpty(type) ? text : $"{type}: {text}";
            }
        }

        // ── Pe obiect ───────────────────────────────────────
        var obj = r.Target ?? throw new RprStepException("Actiunea are nevoie de un obiect.");
        dynamic el = Require(obj, r.TimeoutMs, ct);
        string elType = SafeString(() => (string)el.Type);

        switch (r.Action)
        {
            case RprAction.Click:
                if (elType is "GuiCheckBox") el.Selected = !(bool)el.Selected;
                else if (elType is "GuiRadioButton" or "GuiTab") el.Select();
                else if (elType is "GuiTextField" or "GuiCTextField" or "GuiPasswordField") el.SetFocus();
                else el.Press();
                break;

            case RprAction.DoubleClick:
                if (elType is "GuiGridView") el.DoubleClickCurrentCell();
                else { el.SetFocus(); Session.ActiveWindow.SendVKey(2); } // F2 = dublu click / alegere
                break;

            case RprAction.RightClick:
                el.ShowContextMenu();
                break;

            case RprAction.TypeText:
                el.Text = r.Value;
                break;

            case RprAction.AppendText:
                el.Text = (string)el.Text + r.Value;
                break;

            case RprAction.Clear:
                el.Text = "";
                break;

            case RprAction.Focus:
                el.SetFocus();
                break;

            case RprAction.PressKey:
                el.SetFocus();
                Session.ActiveWindow.SendVKey(SapVKey(r.Value));
                break;

            case RprAction.SelectOption:
                SelectComboEntry(el, r.Value);
                break;

            case RprAction.Check:   el.Selected = true; break;
            case RprAction.Uncheck: el.Selected = false; break;

            case RprAction.ReadText:
            case RprAction.ReadValue:
                return SafeString(() => (string)el.Text);

            case RprAction.ReadAttribute:
                return r.Value.Trim().ToLowerInvariant() switch
                {
                    "id"         => RelativeId((string)el.Id),
                    "name"       => (string)el.Name,
                    "type"       => elType,
                    "tooltip"    => SafeString(() => (string)el.Tooltip),
                    "changeable" => SafeBool(() => (bool)el.Changeable, false).ToString(),
                    _            => SafeString(() => Convert.ToString(el.GetType().InvokeMember(r.Value, BindingFlags.GetProperty, null, el, null))),
                };

            case RprAction.SapGridReadCell:
            {
                var parts = r.Value.Split('|');
                if (parts.Length != 2 || !int.TryParse(parts[0].Trim(), out var row))
                    throw new RprStepException("Valoarea trebuie sa fie \"rand|coloana\" (ex: 0|MATNR sau 0|2).");
                var col = parts[1].Trim();
                if (elType == "GuiTableControl")
                    return (string)el.GetCell(row, int.Parse(col)).Text;
                return (string)el.GetCellValue(row, col); // GuiGridView (ALV)
            }

            case RprAction.SapGridRowCount:
                return ((int)el.RowCount).ToString();

            case RprAction.Highlight:
                el.Visualize(true);
                Thread.Sleep(800);
                el.Visualize(false);
                return null;

            case RprAction.ScreenshotElement:
            {
                Directory.CreateDirectory(r.OutputFolder);
                var path = string.IsNullOrWhiteSpace(r.Value)
                    ? Path.Combine(r.OutputFolder, $"{obj.Name}_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png")
                    : r.Value;
                Session.ActiveWindow.HardCopy(path, 2);
                return path;
            }

            case RprAction.Hover:
                el.SetFocus();
                break;

            default:
                throw new RprStepException($"Actiunea {r.Action} nu e disponibila pentru SAP.");
        }

        WaitWhileBusy(r.TimeoutMs);
        return null;
    }

    private static void SelectComboEntry(dynamic el, string value)
    {
        // GuiComboBox: alegem dupa textul afisat sau dupa cheie
        dynamic entries = el.Entries;
        int count = (int)entries.Count;
        for (int i = 0; i < count; i++)
        {
            dynamic e = entries.Item(i);
            if (string.Equals(((string)e.Value).Trim(), value.Trim(), StringComparison.OrdinalIgnoreCase) ||
                string.Equals(((string)e.Key).Trim(), value.Trim(), StringComparison.OrdinalIgnoreCase))
            {
                el.Key = (string)e.Key;
                return;
            }
        }
        throw new RprStepException($"Optiunea \"{value}\" nu exista in lista SAP.");
    }

    /// <summary>Tastele SAP (SendVKey): Enter=0, F1=1 ... F12=12, Shift+F1=13 ..., Ctrl+S=11.</summary>
    private static int SapVKey(string key)
    {
        var k = key.Trim().ToUpperInvariant().Replace(" ", "");
        if (int.TryParse(k, out var raw)) return raw;
        return k switch
        {
            "ENTER" => 0,
            "CTRL+S" => 11,
            "BACK" or "F3" => 3,
            "EXIT" or "SHIFT+F3" => 15,
            "CANCEL" or "F12" => 12,
            "PAGEUP" or "PGUP" => 81,
            "PAGEDOWN" or "PGDN" => 82,
            "CTRL+F" => 71,
            "CTRL+P" => 86,
            _ when Regex.IsMatch(k, @"^F([1-9]|1[0-2])$") => int.Parse(k[1..]),
            _ when Regex.IsMatch(k, @"^SHIFT\+F([1-9]|1[0-2])$") => 12 + int.Parse(k[7..]),
            _ when Regex.IsMatch(k, @"^CTRL\+F([1-9]|1[0-2])$") => 24 + int.Parse(k[6..]),
            _ when Regex.IsMatch(k, @"^CTRL\+SHIFT\+F([1-9]|1[0-2])$") => 36 + int.Parse(k[12..]),
            _ => throw new RprStepException($"Tasta SAP necunoscuta: \"{key}\". Exemple: Enter, F3, F8, Shift+F4, Ctrl+S sau codul numeric."),
        };
    }

    private static string SafeString(Func<string> f)
    {
        try { return f() ?? ""; } catch (Exception) { return ""; }
    }

    private static bool SafeBool(Func<bool> f, bool fallback)
    {
        try { return f(); } catch (Exception) { return fallback; }
    }

    // =========================================================
    // 4. Spy — elementul SAP de sub mouse; F2 captureaza, Esc anuleaza
    // =========================================================
    public async Task<UiObject?> CaptureObjectAsync(SpyOptions options, CancellationToken ct)
    {
        await _sta.RunAsync(() => { _ = Session; });  // verifica conexiunea inainte
        await Win32.WaitReleaseAsync(Win32.VK_F2, ct);

        string? lastId = null;
        try
        {
            while (true)
            {
                ct.ThrowIfCancellationRequested();
                if (Win32.IsDown(Win32.VK_ESCAPE)) return null;

                Win32.GetCursorPos(out var p);
                bool capture = Win32.IsDown(Win32.VK_F2);

                var result = await _sta.RunAsync<(string? Id, UiObject? Obj)>(() =>
                {
                    string? id = IdAtPosition(p.X, p.Y);
                    if (capture)
                    {
                        // fara pozitie: luam elementul cu focus (click in camp, apoi F2)
                        id ??= SafeString(() => (string)Session.ActiveWindow.GuiFocus.Id);
                        if (string.IsNullOrEmpty(id)) return (null, null);
                        dynamic target = Session.FindById(id);
                        UiObject built = BuildObject(target);
                        return (id, built);
                    }
                    if (id != null && id != lastId)
                    {
                        TryVisualize(lastId, false);
                        TryVisualize(id, true);
                    }
                    return (id, null);
                });

                if (capture)
                {
                    await Win32.WaitReleaseAsync(Win32.VK_F2, ct);
                    if (result.Obj != null) return result.Obj;
                }
                if (result.Id != null) lastId = result.Id;
                await Task.Delay(150, ct);
            }
        }
        finally
        {
            var toClear = lastId;
            await _sta.RunAsync(() => TryVisualize(toClear, false));
        }
    }

    private string? IdAtPosition(int x, int y)
    {
        try
        {
            dynamic hits = Session.FindByPosition(x, y, false);
            int n = (int)hits.Count;
            for (int i = 0; i < n; i++)
            {
                var item = Convert.ToString((object)hits.Item(i));
                if (!string.IsNullOrEmpty(item) && item.StartsWith("/app/", StringComparison.Ordinal))
                    return RelativeId(item);
            }
        }
        catch (Exception) { /* mouse-ul nu e deasupra unei ferestre SAP */ }
        return null;
    }

    private void TryVisualize(string? id, bool on)
    {
        if (string.IsNullOrEmpty(id)) return;
        try { Session.FindById(id, false)?.Visualize(on); } catch (Exception) { }
    }

    private static UiObject BuildObject(dynamic el)
    {
        string id = RelativeId((string)el.Id);
        string type = SafeString(() => (string)el.Type);
        string name = SafeString(() => (string)el.Name);
        string text = SafeString(() => (string)el.Text);
        string tooltip = SafeString(() => (string)el.Tooltip);

        var obj = new UiObject
        {
            Technology = UiTechnology.Sap,
            Name = SuggestName(type, tooltip, text, name),
            ElementType = type,
            CapturedText = text,
            Context = id.Split('/')[0], // wnd[0]
            Locators =
            {
                new Locator(LocatorKind.SapId, id, 90),
            },
            Attributes =
            {
                ["Id"] = id,
                ["Name"] = name,
                ["Type"] = type,
                ["Tooltip"] = tooltip,
            },
        };
        if (!string.IsNullOrWhiteSpace(name) && !string.IsNullOrWhiteSpace(type))
            obj.Locators.Add(new Locator(LocatorKind.SapName, $"{name}|{type}", 60));
        return obj;
    }

    private static string SuggestName(string type, string tooltip, string text, string technicalName)
    {
        var prefix = type switch
        {
            "GuiButton" => "Buton",
            "GuiTextField" or "GuiCTextField" or "GuiPasswordField" => "Camp",
            "GuiComboBox" => "Lista",
            "GuiCheckBox" => "Bifa",
            "GuiRadioButton" => "Optiune",
            "GuiTab" => "Tab",
            "GuiGridView" or "GuiTableControl" => "Tabel",
            "GuiLabel" => "Text",
            "GuiStatusbar" => "BaraStare",
            _ => "SAP",
        };
        // tooltip-ul SAP contine de obicei eticheta campului ("Material (F4)")
        var basis = !string.IsNullOrWhiteSpace(tooltip) ? Regex.Replace(tooltip, @"\(.*?\)", "")
                  : type == "GuiButton" && !string.IsNullOrWhiteSpace(text) ? text
                  : technicalName;
        var clean = Regex.Replace(basis.Normalize(System.Text.NormalizationForm.FormD), @"\p{Mn}", "");
        clean = Regex.Replace(clean, @"[^A-Za-z0-9]+", "_").Trim('_');
        if (clean.Length > 30) clean = clean[..30];
        return string.IsNullOrEmpty(clean) ? prefix : $"{prefix}_{clean}";
    }

    public ValueTask DisposeAsync()
    {
        _session = null;
        _sta.Dispose();
        return ValueTask.CompletedTask;
    }
}
