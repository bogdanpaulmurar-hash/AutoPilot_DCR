// ============================================================
// AutoPilot DC v4 — RPR
// RprStorage.cs — Salvare/incarcare rutine si Object Repository (JSON)
// + conversia rutinelor vechi v3.9 + exportul logului in Excel.
// ============================================================

using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using ClosedXML.Excel;
using AutoPilotDC.Models;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Storage;

/// <summary>Foldere de lucru: %AppData%\AutoPilotDC\Studio\...</summary>
public static class RprPaths
{
    public static string Root { get; set; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "AutoPilotDC", "Studio");

    public static string Routines => Ensure(Path.Combine(Root, "rutine"));
    public static string Output => Ensure(Path.Combine(Root, "rezultate"));
    public static string ObjectImages => Ensure(Path.Combine(Root, "obiecte"));
    public static string BrowserProfile => Ensure(Path.Combine(Root, "browser-profil"));
    public static string DefaultRepository => Path.Combine(Ensure(Root), "obiecte.json");

    private static string Ensure(string p) { Directory.CreateDirectory(p); return p; }
}

public static class RprJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping, // diacritice lizibile in fisier
        Converters = { new JsonStringEnumConverter() },
    };
}

public static class RoutineStore
{
    // 1. Incarcare — accepta formatul nou (v2) si rutinele vechi v3.9
    public static Routine Load(string path, ObjectRepository? repoForLegacyImport = null)
    {
        var json = File.ReadAllText(path);
        var root = JsonNode.Parse(json);

        bool isNew = root is JsonObject o && o.ContainsKey("format_version");
        if (isNew)
            return JsonSerializer.Deserialize<Routine>(json, RprJson.Options)
                   ?? throw new InvalidDataException("Fisier de rutina gol.");

        // Format vechi: { "name", "steps": [StepModel...] } sau direct [StepModel...]
        var legacyOpts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        List<StepModel> steps;
        string name = Path.GetFileNameWithoutExtension(path);
        if (root is JsonArray)
        {
            steps = JsonSerializer.Deserialize<List<StepModel>>(json, legacyOpts) ?? new();
        }
        else
        {
            var rf = JsonSerializer.Deserialize<RoutineFile>(json, legacyOpts) ?? new RoutineFile();
            steps = rf.Steps;
            if (!string.IsNullOrWhiteSpace(rf.Name)) name = rf.Name;
        }
        return LegacyConverter.Convert(name, steps, repoForLegacyImport);
    }

    // 2. Salvare atomica (scriem in .tmp apoi inlocuim — nu pierdem rutina la crash)
    public static void Save(Routine routine, string path)
    {
        routine.ModifiedAt = DateTime.Now;
        var json = JsonSerializer.Serialize(routine, RprJson.Options);
        AtomicWrite(path, json);
    }

    public static string DefaultPathFor(Routine routine) =>
        Path.Combine(RprPaths.Routines, ObjectRepository.Sanitize(routine.Name) + ".rpr.json");

    internal static void AtomicWrite(string path, string content)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, content);
        if (File.Exists(path)) File.Replace(tmp, path, null);
        else File.Move(tmp, path);
    }
}

public static class RepositoryStore
{
    public static ObjectRepository Load(string? path)
    {
        path = string.IsNullOrWhiteSpace(path) ? RprPaths.DefaultRepository : path;
        if (!File.Exists(path)) return new ObjectRepository();
        return JsonSerializer.Deserialize<ObjectRepository>(File.ReadAllText(path), RprJson.Options)
               ?? new ObjectRepository();
    }

    public static void Save(ObjectRepository repo, string? path)
    {
        path = string.IsNullOrWhiteSpace(path) ? RprPaths.DefaultRepository : path;
        RoutineStore.AtomicWrite(path, JsonSerializer.Serialize(repo, RprJson.Options));
    }
}

/// <summary>Transforma rutinele vechi (coordonate) in pasi noi, unde se poate.</summary>
public static class LegacyConverter
{
    public static Routine Convert(string name, IEnumerable<StepModel> steps, ObjectRepository? repo = null)
    {
        var routine = new Routine { Name = name, Description = "Convertita automat din v3.9" };
        foreach (var s in steps)
        {
            // Pasi de browser cu selector -> obiect in repository + actiune pe obiect
            if (repo != null && s.StepType is "browser_click" or "browser_fill" or "browser_wait"
                && !string.IsNullOrWhiteSpace(s.KeyCombo))
            {
                var obj = repo.Objects.FirstOrDefault(o => o.Locators.Any(l => l.Value == s.KeyCombo.Trim()))
                          ?? repo.Add(new UiObject
                          {
                              Name = string.IsNullOrWhiteSpace(s.Description) ? "Web_Element" : s.Description,
                              Technology = UiTechnology.Web,
                              Locators = { SelectorToLocator(s.KeyCombo.Trim()) },
                              Description = "Importat din v3.9",
                          });
                RprNode web = s.StepType switch
                {
                    "browser_click" => new ActionNode { Action = RprAction.Click, Target = obj.Name },
                    "browser_fill"  => new ActionNode { Action = RprAction.TypeText, Target = obj.Name, Value = s.TextInput },
                    _               => new WaitNode { Mode = WaitMode.UntilTrue, Condition = new Condition { Kind = ConditionKind.ElementVisible, Target = obj.Name } },
                };
                web.Enabled = !s.Skip;
                web.Comment = s.Comment;
                routine.Steps.Add(web);
                continue;
            }

            RprNode node = s.StepType switch
            {
                // Pasii de browser aveau selectorul in KeyCombo -> devin actiuni pe obiecte web
                "browser_open"     => new ActionNode { Action = RprAction.OpenBrowser, Technology = UiTechnology.Web, Value = s.TextInput },
                "browser_navigate" => new ActionNode { Action = RprAction.Navigate, Technology = UiTechnology.Web, Value = s.TextInput },
                "browser_close"    => new ActionNode { Action = RprAction.CloseBrowser, Technology = UiTechnology.Web },
                "DELAY"            => new WaitNode { Seconds = Math.Max(s.DelayAfter, s.DelayBefore) },
                "QUESTION"         => new QuestionNode { Text = s.QuestionText, Buttons = s.QuestionButtons },
                _                  => new LegacyStepNode { Step = s },
            };
            node.Enabled = !s.Skip;
            node.Comment = s.Comment;
            if (s.StepType != "DELAY")
            {
                node.DelayBeforeMs = (int)(s.DelayBefore * 1000);
                node.DelayAfterMs = (int)(s.DelayAfter * 1000);
                // intarzierile trec pe nod; motorul vechi nu le mai aplica a doua oara
                s.DelayBefore = 0;
                s.DelayAfter = 0;
            }
            routine.Steps.Add(node);
        }
        return routine;
    }

    private static Locator SelectorToLocator(string selector)
    {
        if (selector.StartsWith("//") || selector.StartsWith("xpath=", StringComparison.OrdinalIgnoreCase))
            return new Locator(LocatorKind.XPath, selector.Replace("xpath=", "", StringComparison.OrdinalIgnoreCase), 40);
        if (selector.StartsWith("text=", StringComparison.OrdinalIgnoreCase))
            return new Locator(LocatorKind.Text, selector[5..], 50);
        return new Locator(LocatorKind.Css, selector.Replace("css=", "", StringComparison.OrdinalIgnoreCase), 50);
    }
}

/// <summary>Exportul logului de rulare in Excel (randurile cu erori colorate).</summary>
public static class RunLogExporter
{
    public static void ExportXlsx(IEnumerable<RunLogEntry> entries, string path)
    {
        using var wb = new XLWorkbook();
        var ws = wb.AddWorksheet("Log");
        string[] headers = { "Ora", "Nivel", "Rand Excel", "Pas", "Mesaj", "Durata (ms)", "Captura" };
        for (int c = 0; c < headers.Length; c++)
        {
            ws.Cell(1, c + 1).Value = headers[c];
            ws.Cell(1, c + 1).Style.Font.Bold = true;
            ws.Cell(1, c + 1).Style.Fill.BackgroundColor = XLColor.FromHtml("#009999");
            ws.Cell(1, c + 1).Style.Font.FontColor = XLColor.White;
        }

        int r = 2;
        foreach (var e in entries)
        {
            ws.Cell(r, 1).Value = e.Time.ToString("yyyy-MM-dd HH:mm:ss");
            ws.Cell(r, 2).Value = e.Level.ToString();
            if (e.ExcelRow > 0) ws.Cell(r, 3).Value = e.ExcelRow;
            ws.Cell(r, 4).Value = e.NodeTitle;
            ws.Cell(r, 5).Value = e.Message;
            if (e.DurationMs > 0) ws.Cell(r, 6).Value = Math.Round(e.DurationMs);
            ws.Cell(r, 7).Value = e.Screenshot;
            if (e.Level == RprLogLevel.Error)
                ws.Range(r, 1, r, headers.Length).Style.Fill.BackgroundColor = XLColor.FromHtml("#FFC7CE");
            else if (e.Level == RprLogLevel.Warning)
                ws.Range(r, 1, r, headers.Length).Style.Fill.BackgroundColor = XLColor.FromHtml("#FFEB9C");
            r++;
        }
        ws.Columns().AdjustToContents();
        ws.SheetView.FreezeRows(1);
        wb.SaveAs(path);
    }
}
