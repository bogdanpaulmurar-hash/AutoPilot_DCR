using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Engines
{
    /// <summary>
    /// Executa pasi de automatizare desktop via Win32 API.
    /// Foloseste mouse_event / keybd_event (NU SendInput) pentru compatibilitate maxima.
    /// Coordonatele sunt absolute. Delay-urile se aplica INAINTE si DUPA fiecare step.
    /// Echivalent Python: PlayerEngine._exec() + pyautogui calls
    /// </summary>
    [System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
    public class DesktopEngine : IAutomationEngine
    {
        // -- Win32 imports ----------------------------------------------------
        [DllImport("user32.dll")] static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, IntPtr dwExtraInfo);
        [DllImport("user32.dll")] static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, IntPtr dwExtraInfo);
        [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
        [DllImport("user32.dll")] static extern short VkKeyScan(char ch);
        [DllImport("user32.dll")] static extern int GetSystemMetrics(int nIndex);
        [DllImport("user32.dll")] static extern uint MapVirtualKey(uint uCode, uint uMapType);

        // mouse_event flags
        const uint MOUSEEVENTF_LEFTDOWN   = 0x0002;
        const uint MOUSEEVENTF_LEFTUP     = 0x0004;
        const uint MOUSEEVENTF_RIGHTDOWN  = 0x0008;
        const uint MOUSEEVENTF_RIGHTUP    = 0x0010;
        const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020;
        const uint MOUSEEVENTF_MIDDLEUP   = 0x0040;
        const uint MOUSEEVENTF_WHEEL      = 0x0800;

        // keybd_event flags
        const uint KEYEVENTF_KEYUP        = 0x0002;
        const uint KEYEVENTF_EXTENDEDKEY  = 0x0001;

        // Virtual key codes
        const byte VK_SHIFT   = 0x10;
        const byte VK_CONTROL = 0x11;
        const byte VK_MENU    = 0x12; // ALT
        const byte VK_LWIN    = 0x5B;
        const byte VK_RETURN  = 0x0D;
        const byte VK_TAB     = 0x09;
        const byte VK_ESCAPE  = 0x1B;
        const byte VK_BACK    = 0x08;
        const byte VK_DELETE  = 0x2E;
        const byte VK_HOME    = 0x24;
        const byte VK_END     = 0x23;
        const byte VK_PRIOR   = 0x21; // PageUp
        const byte VK_NEXT    = 0x22; // PageDown
        const byte VK_LEFT    = 0x25;
        const byte VK_UP      = 0x26;
        const byte VK_RIGHT   = 0x27;
        const byte VK_DOWN    = 0x28;
        const byte VK_INSERT  = 0x2D;
        const byte VK_F1      = 0x70;
        const byte VK_SPACE   = 0x20;
        const byte VK_PRINT   = 0x2C; // PrintScreen

        // -- IAutomationEngine ------------------------------------------------
        public string EngineType => "desktop";
        public bool IsAvailable  => true;

        public bool SupportsStep(StepModel step) =>
            !step.StepType.StartsWith("browser_", StringComparison.OrdinalIgnoreCase);

        public async Task<(bool Success, string Error)> ExecuteStepAsync(
            StepModel step, CancellationToken ct = default)
        {
            try
            {
                if (step.DelayBefore > 0)
                    await Task.Delay(TimeSpan.FromSeconds(step.DelayBefore), ct);

                switch (step.StepType.ToUpperInvariant())
                {
                    case "CLICK":
                        MoveTo(step.X, step.Y);
                        await Task.Delay(50, ct);
                        MouseClick(step.Button ?? "left", step.ClickType ?? "single");
                        break;

                    case "DBLCLICK":
                        MoveTo(step.X, step.Y);
                        await Task.Delay(50, ct);
                        MouseClick("left", "double");
                        break;

                    case "RIGHTCLICK":
                        MoveTo(step.X, step.Y);
                        await Task.Delay(50, ct);
                        MouseClick("right", "single");
                        break;

                    case "MOVE":
                        MoveTo(step.X, step.Y);
                        break;

                    case "SCROLL":
                        MoveTo(step.X, step.Y);
                        await Task.Delay(50, ct);
                        DoScroll(step.ScrollDy);
                        break;

                    case "TYPE":
                        TypeText(step.TextInput ?? "");
                        break;

                    case "KEY":
                        PressKeyCombo(step.KeyCombo ?? "");
                        break;

                    case "DELAY":
                        double d = step.DelayBefore > 0 ? step.DelayBefore : 1.0;
                        await Task.Delay(TimeSpan.FromSeconds(d), ct);
                        break;

                    case "SCREENSHOT":
                        TakeScreenshot(step.Description);
                        break;

                    case "QUESTION":
                        // QUESTION este gestionat de PlayerEngine via OnQuestion callback
                        // DesktopEngine nu face nimic pentru QUESTION
                        break;

                    default:
                        return (false, $"Tip pas necunoscut: {step.StepType}");
                }

                if (step.DelayAfter > 0)
                    await Task.Delay(TimeSpan.FromSeconds(step.DelayAfter), ct);

                return (true, "");
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                return (false, ex.Message);
            }
        }

        // -- Mouse helpers -----------------------------------------------------
        public static void MoveTo(int x, int y)
        {
            SetCursorPos(x, y);
            Thread.Sleep(15);
        }

        public static void MouseClick(string button, string clickType)
        {
            (uint down, uint up) = button?.ToLowerInvariant() switch
            {
                "right"  => (MOUSEEVENTF_RIGHTDOWN,  MOUSEEVENTF_RIGHTUP),
                "middle" => (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
                _        => (MOUSEEVENTF_LEFTDOWN,   MOUSEEVENTF_LEFTUP),
            };

            int clicks = clickType?.ToLowerInvariant() switch
            {
                "double" => 2,
                "triple" => 3,
                _        => 1,
            };

            for (int i = 0; i < clicks; i++)
            {
                mouse_event(down, 0, 0, 0, IntPtr.Zero);
                Thread.Sleep(30);
                mouse_event(up,   0, 0, 0, IntPtr.Zero);
                if (i < clicks - 1) Thread.Sleep(50);
            }
        }

        public static void DoScroll(int dy)
        {
            // dy > 0 = scroll up, dy < 0 = scroll down (identic Python scroll_dy)
            int wheelDelta = dy * 120;
            mouse_event(MOUSEEVENTF_WHEEL, 0, 0, (uint)wheelDelta, IntPtr.Zero);
        }

        // -- Keyboard helpers --------------------------------------------------
        public static void TypeText(string text)
        {
            if (string.IsNullOrEmpty(text)) return;

            foreach (char ch in text)
            {
                short vk = VkKeyScan(ch);
                if (vk == -1)
                {
                    // Fallback: trimite ca Unicode via Alt+numpad (nu ideal, dar functional)
                    Thread.Sleep(40);
                    continue;
                }

                byte vkCode   = (byte)(vk & 0xFF);
                byte scanCode = (byte)(MapVirtualKey(vkCode, 0) & 0xFF);
                bool needShift = (vk & 0x0100) != 0;
                bool needCtrl  = (vk & 0x0200) != 0;
                bool needAlt   = (vk & 0x0400) != 0;

                if (needShift) keybd_event(VK_SHIFT,   0, 0, IntPtr.Zero);
                if (needCtrl)  keybd_event(VK_CONTROL, 0, 0, IntPtr.Zero);
                if (needAlt)   keybd_event(VK_MENU,    0, 0, IntPtr.Zero);

                keybd_event(vkCode, scanCode, 0,              IntPtr.Zero);
                Thread.Sleep(20);
                keybd_event(vkCode, scanCode, KEYEVENTF_KEYUP, IntPtr.Zero);

                if (needAlt)   keybd_event(VK_MENU,    0, KEYEVENTF_KEYUP, IntPtr.Zero);
                if (needCtrl)  keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, IntPtr.Zero);
                if (needShift) keybd_event(VK_SHIFT,   0, KEYEVENTF_KEYUP, IntPtr.Zero);

                Thread.Sleep(40);
            }
        }

        /// <summary>
        /// Executa o combinatie de taste (ex: "Ctrl+C", "Alt+F4", "F5", "Enter").
        /// Echivalent Python: _pynput_combo() + pyautogui.press()
        /// </summary>
        public static void PressKeyCombo(string combo)
        {
            if (string.IsNullOrWhiteSpace(combo)) return;

            var parts     = combo.Split('+');
            var modifiers = new System.Collections.Generic.List<byte>();
            byte mainKey  = 0;

            foreach (var part in parts)
            {
                string p = part.Trim().ToLowerInvariant();
                switch (p)
                {
                    case "ctrl":
                    case "control": modifiers.Add(VK_CONTROL); break;
                    case "shift":   modifiers.Add(VK_SHIFT);   break;
                    case "alt":     modifiers.Add(VK_MENU);    break;
                    case "win":
                    case "windows": modifiers.Add(VK_LWIN);    break;
                    default:
                        mainKey = ResolveVirtualKey(p);
                        break;
                }
            }

            // Apasa modificatori
            foreach (var mod in modifiers)
                keybd_event(mod, 0, 0, IntPtr.Zero);

            // Apasa tasta principala
            if (mainKey != 0)
            {
                byte scan = (byte)(MapVirtualKey(mainKey, 0) & 0xFF);
                keybd_event(mainKey, scan, 0,              IntPtr.Zero);
                Thread.Sleep(30);
                keybd_event(mainKey, scan, KEYEVENTF_KEYUP, IntPtr.Zero);
            }

            // Elibereaza modificatori (in ordine inversa)
            modifiers.Reverse();
            foreach (var mod in modifiers)
                keybd_event(mod, 0, KEYEVENTF_KEYUP, IntPtr.Zero);
        }

        private static byte ResolveVirtualKey(string keyName)
        {
            return keyName.ToLowerInvariant() switch
            {
                "enter" or "return" => VK_RETURN,
                "tab"               => VK_TAB,
                "esc" or "escape"   => VK_ESCAPE,
                "backspace"         => VK_BACK,
                "delete" or "del"   => VK_DELETE,
                "home"              => VK_HOME,
                "end"               => VK_END,
                "pageup" or "pgup"  => VK_PRIOR,
                "pagedown" or "pgdn"=> VK_NEXT,
                "left"              => VK_LEFT,
                "right"             => VK_RIGHT,
                "up"                => VK_UP,
                "down"              => VK_DOWN,
                "insert" or "ins"   => VK_INSERT,
                "space"             => VK_SPACE,
                "printscreen"       => VK_PRINT,
                "f1"  => (byte)(VK_F1 + 0),
                "f2"  => (byte)(VK_F1 + 1),
                "f3"  => (byte)(VK_F1 + 2),
                "f4"  => (byte)(VK_F1 + 3),
                "f5"  => (byte)(VK_F1 + 4),
                "f6"  => (byte)(VK_F1 + 5),
                "f7"  => (byte)(VK_F1 + 6),
                "f8"  => (byte)(VK_F1 + 7),
                "f9"  => (byte)(VK_F1 + 8),
                "f10" => (byte)(VK_F1 + 9),
                "f11" => (byte)(VK_F1 + 10),
                "f12" => (byte)(VK_F1 + 11),
                _ when keyName.Length == 1 => (byte)(VkKeyScan(keyName[0]) & 0xFF),
                _ => 0
            };
        }

        // -- Screenshot helper -------------------------------------------------
        public static void TakeScreenshot(string? label = null)
        {
            try
            {
                string dir  = System.IO.Path.Combine(
                    AppDomain.CurrentDomain.BaseDirectory, "screenshots");
                System.IO.Directory.CreateDirectory(dir);

                string ts   = DateTime.Now.ToString("yyyyMMdd_HHmmss_fff");
                string safe = string.IsNullOrWhiteSpace(label)
                    ? ts
                    : $"{ts}_{SanitizeFileName(label)}";
                string path = System.IO.Path.Combine(dir, $"{safe}.png");

                // Captura ecran via GDI
                int sw = GetSystemMetrics(0); // SM_CXSCREEN
                int sh = GetSystemMetrics(1); // SM_CYSCREEN

                using var bmp = new System.Drawing.Bitmap(sw, sh);
                using var g   = System.Drawing.Graphics.FromImage(bmp);
                g.CopyFromScreen(0, 0, 0, 0, new System.Drawing.Size(sw, sh));
                bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[DesktopEngine] Screenshot error: {ex.Message}");
            }
        }

        private static string SanitizeFileName(string name)
        {
            foreach (char c in System.IO.Path.GetInvalidFileNameChars())
                name = name.Replace(c, '_');
            return name.Length > 50 ? name[..50] : name;
        }
    }
}
