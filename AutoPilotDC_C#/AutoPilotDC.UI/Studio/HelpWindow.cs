// ============================================================
// AutoPilot DC v4 — Studio RPR
// HelpWindow.cs — Ghidul pas cu pas (docs/GHID_STUDIO_RPR.md),
// incorporat in aplicatie si afisat cu cuprins + cautare.
// Suporta un subset simplu de Markdown: #, ##, ###, liste, **bold**, `cod`.
// ============================================================

using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using Brush = System.Windows.Media.Brush;
using Color = System.Windows.Media.Color;
using FontFamily = System.Windows.Media.FontFamily;
using HorizontalAlignment = System.Windows.HorizontalAlignment;
using ListBox = System.Windows.Controls.ListBox;
using TextBox = System.Windows.Controls.TextBox;

namespace AutoPilotDC.UI.Studio;

public sealed class HelpWindow : Window
{
    private static HelpWindow? _open;

    private readonly FlowDocumentScrollViewer _viewer = new();
    private readonly ListBox _toc = new();
    private readonly List<(string Title, Block Block)> _sections = new();
    private readonly string _markdown;

    public static void ShowGuide(Window owner)
    {
        if (_open != null) { _open.Activate(); return; }
        _open = new HelpWindow { Owner = owner };
        _open.Closed += (_, _) => _open = null;
        _open.Show();
    }

    private HelpWindow()
    {
        Ui.Themed(this);
        Title = "Ghid Studio RPR — instructiuni pas cu pas";
        Width = 1100;
        Height = 820;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;

        _markdown = LoadGuide();

        var root = new Grid();
        root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(300) });
        root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        // ── Stanga: cautare + cuprins ──
        var left = new DockPanel { Margin = new Thickness(10) };
        var search = new TextBox { Margin = new Thickness(0, 0, 0, 8), ToolTip = "Cauta in ghid" };
        DockPanel.SetDock(search, Dock.Top);
        left.Children.Add(Ui.Text("Cuprins", 15, true, "PrimaryBrush"));
        DockPanel.SetDock(left.Children[0], Dock.Top);
        left.Children.Add(search);
        left.Children.Add(_toc);
        Grid.SetColumn(left, 0);
        root.Children.Add(left);

        // ── Dreapta: documentul ──
        _viewer.Margin = new Thickness(0, 10, 10, 10);
        _viewer.VerticalScrollBarVisibility = ScrollBarVisibility.Auto;
        Grid.SetColumn(_viewer, 1);
        root.Children.Add(_viewer);

        Content = root;

        Render();
        _toc.SelectionChanged += (_, _) =>
        {
            if (_toc.SelectedIndex >= 0 && _toc.SelectedIndex < _sections.Count)
                _sections[_toc.SelectedIndex].Block.BringIntoView();
        };
        search.TextChanged += (_, _) => Highlight(search.Text.Trim());
    }

    private static string LoadGuide()
    {
        var asm = Assembly.GetExecutingAssembly();
        using var s = asm.GetManifestResourceStream("AutoPilotDC.UI.Ghid.md");
        if (s == null) return "# Ghid\n\nGhidul nu a fost gasit in aplicatie. Vezi docs/GHID_STUDIO_RPR.md in repository.";
        using var r = new StreamReader(s);
        return r.ReadToEnd();
    }

    // =========================================================
    // Markdown -> FlowDocument
    // =========================================================
    private void Render(string? highlight = null)
    {
        _sections.Clear();
        _toc.Items.Clear();

        var doc = new FlowDocument
        {
            FontFamily = new FontFamily("Segoe UI"),
            FontSize = 14,
            PagePadding = new Thickness(24, 12, 24, 24),
            LineHeight = 22,
            TextAlignment = TextAlignment.Left,
        };
        doc.SetResourceReference(FlowDocument.ForegroundProperty, "TextBrush");
        doc.SetResourceReference(FlowDocument.BackgroundProperty, "BgMainBrush");

        List? currentList = null;
        foreach (var rawLine in _markdown.Replace("\r", "").Split('\n'))
        {
            var line = rawLine.TrimEnd();

            if (line.StartsWith("- ") || System.Text.RegularExpressions.Regex.IsMatch(line, @"^\d+\. "))
            {
                bool numbered = !line.StartsWith("- ");
                if (currentList == null || (currentList.MarkerStyle == TextMarkerStyle.Decimal) != numbered)
                {
                    currentList = new List { MarkerStyle = numbered ? TextMarkerStyle.Decimal : TextMarkerStyle.Disc, Margin = new Thickness(0, 2, 0, 8), Padding = new Thickness(22, 0, 0, 0) };
                    doc.Blocks.Add(currentList);
                }
                var text = numbered ? line[(line.IndexOf(". ", StringComparison.Ordinal) + 2)..] : line[2..];
                currentList.ListItems.Add(new ListItem(Inline(text, highlight)) { Margin = new Thickness(0, 2, 0, 2) });
                continue;
            }
            currentList = null;

            if (string.IsNullOrWhiteSpace(line)) continue;

            if (line.StartsWith("### "))
            {
                var p = Inline(line[4..], highlight);
                p.FontSize = 16; p.FontWeight = FontWeights.SemiBold; p.Margin = new Thickness(0, 12, 0, 4);
                p.SetResourceReference(Paragraph.ForegroundProperty, "AccentBrush");
                doc.Blocks.Add(p);
            }
            else if (line.StartsWith("## "))
            {
                var p = Inline(line[3..], highlight);
                p.FontSize = 20; p.FontWeight = FontWeights.Bold; p.Margin = new Thickness(0, 22, 0, 6);
                p.SetResourceReference(Paragraph.ForegroundProperty, "PrimaryBrush");
                doc.Blocks.Add(p);
                _sections.Add((line[3..], p));
                _toc.Items.Add(new ListBoxItem { Content = line[3..] });
            }
            else if (line.StartsWith("# "))
            {
                var p = Inline(line[2..], highlight);
                p.FontSize = 26; p.FontWeight = FontWeights.Bold; p.Margin = new Thickness(0, 0, 0, 10);
                p.SetResourceReference(Paragraph.ForegroundProperty, "PrimaryBrush");
                doc.Blocks.Add(p);
            }
            else
            {
                var p = Inline(line, highlight);
                p.Margin = new Thickness(0, 4, 0, 6);
                doc.Blocks.Add(p);
            }
        }
        _viewer.Document = doc;
    }

    /// <summary>**bold**, `cod` si evidentierea textului cautat.</summary>
    private static Paragraph Inline(string text, string? highlight)
    {
        var p = new Paragraph();
        var parts = System.Text.RegularExpressions.Regex.Split(text, @"(\*\*[^*]+\*\*|`[^`]+`)");
        foreach (var part in parts)
        {
            if (part.Length == 0) continue;
            if (part.StartsWith("**") && part.EndsWith("**") && part.Length > 4)
                AddRuns(p, part[2..^2], highlight, bold: true, code: false);
            else if (part.StartsWith('`') && part.EndsWith('`') && part.Length > 2)
                AddRuns(p, part[1..^1], highlight, bold: false, code: true);
            else
                AddRuns(p, part, highlight, bold: false, code: false);
        }
        return p;
    }

    private static void AddRuns(Paragraph p, string text, string? highlight, bool bold, bool code)
    {
        Run Make(string s, bool hit)
        {
            var r = new Run(s);
            if (bold) r.FontWeight = FontWeights.SemiBold;
            if (code)
            {
                r.FontFamily = new FontFamily("Consolas");
                r.SetResourceReference(TextElement.BackgroundProperty, "BgCardBrush");
            }
            if (hit)
            {
                r.Background = new SolidColorBrush(Color.FromRgb(255, 215, 0));
                r.Foreground = new SolidColorBrush(Color.FromRgb(0, 0, 40));
            }
            return r;
        }

        if (string.IsNullOrEmpty(highlight))
        {
            p.Inlines.Add(Make(text, false));
            return;
        }
        int i = 0;
        while (i < text.Length)
        {
            int j = text.IndexOf(highlight, i, StringComparison.OrdinalIgnoreCase);
            if (j < 0) { p.Inlines.Add(Make(text[i..], false)); break; }
            if (j > i) p.Inlines.Add(Make(text[i..j], false));
            p.Inlines.Add(Make(text.Substring(j, highlight.Length), true));
            i = j + highlight.Length;
        }
    }

    private void Highlight(string term)
    {
        Render(term.Length >= 2 ? term : null);
        if (term.Length < 2) return;
        // sari la prima sectiune care contine termenul
        for (int i = 0; i < _sections.Count; i++)
        {
            var start = _markdown.IndexOf("## " + _sections[i].Title, StringComparison.Ordinal);
            var end = i + 1 < _sections.Count ? _markdown.IndexOf("## " + _sections[i + 1].Title, StringComparison.Ordinal) : _markdown.Length;
            if (start >= 0 && end > start && _markdown[start..end].Contains(term, StringComparison.OrdinalIgnoreCase))
            {
                _toc.SelectedIndex = i;
                break;
            }
        }
    }
}
