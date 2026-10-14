// ============================================================
// AutoPilot DC v4 — RPR
// ExcelTable.cs — Excel ca sursa de date pentru "Pentru fiecare rand"
// Citeste randuri dupa titlul coloanei, scrie rezultate inapoi,
// coloreaza randurile, creeaza coloane noi la nevoie.
// ============================================================

using ClosedXML.Excel;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Excel;

public sealed class ExcelTable : IDisposable
{
    private readonly XLWorkbook _wb;
    private readonly IXLWorksheet _ws;
    private readonly Dictionary<string, int> _headers = new(StringComparer.OrdinalIgnoreCase);

    public string FilePath { get; }
    public int HeaderRow { get; }
    public string SheetName => _ws.Name;
    public IReadOnlyDictionary<string, int> Headers => _headers;

    private ExcelTable(string path, XLWorkbook wb, IXLWorksheet ws, int headerRow)
    {
        FilePath = path;
        _wb = wb;
        _ws = ws;
        HeaderRow = headerRow;
        LoadHeaders();
    }

    // ─────────────────────────────────────────────────────────
    // 1. Deschidere cu mesaje clare (fisier lipsa / deschis in Excel)
    // ─────────────────────────────────────────────────────────
    public static ExcelTable Open(string path, string? sheet, int headerRow)
    {
        if (string.IsNullOrWhiteSpace(path))
            throw new RprStepException("Nu ai ales fisierul Excel.");
        if (!File.Exists(path))
            throw new RprStepException($"Fisierul Excel nu exista: {path}");

        XLWorkbook wb;
        try
        {
            wb = new XLWorkbook(path);
        }
        catch (IOException ex)
        {
            throw new RprStepException($"Fisierul {Path.GetFileName(path)} e blocat (probabil deschis in Excel). Inchide-l si porneste din nou. ({ex.Message})", ex);
        }

        IXLWorksheet ws;
        if (string.IsNullOrWhiteSpace(sheet))
            ws = wb.Worksheet(1);
        else if (!wb.TryGetWorksheet(sheet, out ws!))
        {
            var names = string.Join(", ", wb.Worksheets.Select(w => w.Name));
            wb.Dispose();
            throw new RprStepException($"Foaia \"{sheet}\" nu exista. Foi disponibile: {names}");
        }

        return new ExcelTable(path, wb, ws, Math.Max(0, headerRow));
    }

    public static IReadOnlyList<string> GetSheetNames(string path)
    {
        using var wb = new XLWorkbook(path);
        return wb.Worksheets.Select(w => w.Name).ToList();
    }

    private void LoadHeaders()
    {
        _headers.Clear();
        if (HeaderRow <= 0) return;
        var row = _ws.Row(HeaderRow);
        int last = row.LastCellUsed()?.Address.ColumnNumber ?? 0;
        for (int col = 1; col <= last; col++)
        {
            var title = row.Cell(col).GetString().Trim();
            if (title.Length > 0 && !_headers.ContainsKey(title))
                _headers[title] = col;
        }
    }

    // ─────────────────────────────────────────────────────────
    // 2. Rezolvare coloana: titlu ("IBase") sau litera ("C")
    // ─────────────────────────────────────────────────────────
    public int? ResolveColumn(string column)
    {
        if (string.IsNullOrWhiteSpace(column)) return null;
        column = column.Trim();
        if (_headers.TryGetValue(column, out var byTitle)) return byTitle;
        if (System.Text.RegularExpressions.Regex.IsMatch(column, "^[A-Za-z]{1,3}$"))
            return XLHelper.GetColumnNumberFromLetter(column.ToUpperInvariant());
        return null;
    }

    /// <summary>Returneaza coloana; daca nu exista si avem rand de titluri, o creeaza la final.</summary>
    public int GetOrCreateColumn(string column)
    {
        var existing = ResolveColumn(column);
        if (existing.HasValue) return existing.Value;
        if (HeaderRow <= 0)
            throw new RprStepException($"Coloana \"{column}\" nu exista. Fara rand de titluri foloseste litere (A, B, C...).");

        int newCol = Math.Max(_headers.Count == 0 ? 0 : _headers.Values.Max(),
                              _ws.Row(HeaderRow).LastCellUsed()?.Address.ColumnNumber ?? 0) + 1;
        var cell = _ws.Cell(HeaderRow, newCol);
        cell.Value = column.Trim();
        cell.Style.Font.Bold = true;
        _headers[column.Trim()] = newCol;
        return newCol;
    }

    public int FirstDataRow(int startRow) => startRow > 0 ? startRow : HeaderRow + 1;

    /// <summary>Ultimul rand cu date in coloana cheie (sau in foaie).</summary>
    public int LastDataRow(string keyColumn)
    {
        var col = ResolveColumn(keyColumn);
        if (col.HasValue)
            return _ws.Column(col.Value).LastCellUsed()?.Address.RowNumber ?? 0;
        return _ws.LastRowUsed()?.RowNumber() ?? 0;
    }

    public bool IsRowEmpty(int row, string keyColumn)
    {
        var col = ResolveColumn(keyColumn);
        if (col.HasValue) return string.IsNullOrWhiteSpace(_ws.Cell(row, col.Value).GetString());
        return _ws.Row(row).IsEmpty();
    }

    // ─────────────────────────────────────────────────────────
    // 3. Citire rand -> variabile {Prefix.Titlu}, {Prefix.A}, {Prefix.#}
    // ─────────────────────────────────────────────────────────
    public void LoadRowInto(VariableStore vars, string prefix, int row)
    {
        vars.RemovePrefix(prefix + ".");
        vars.Set($"{prefix}.#", row.ToString());

        int last = Math.Max(_ws.Row(row).LastCellUsed()?.Address.ColumnNumber ?? 0,
                            _headers.Count == 0 ? 0 : _headers.Values.Max());
        for (int col = 1; col <= last; col++)
        {
            var value = _ws.Cell(row, col).GetFormattedString();
            vars.Set($"{prefix}.{XLHelper.GetColumnLetterFromNumber(col)}", value);
        }
        foreach (var (title, col) in _headers)
            vars.Set($"{prefix}.{title}", _ws.Cell(row, col).GetFormattedString());
    }

    public string GetCell(int row, string column)
    {
        var col = ResolveColumn(column);
        return col.HasValue ? _ws.Cell(row, col.Value).GetFormattedString() : "";
    }

    // ─────────────────────────────────────────────────────────
    // 4. Scriere + culori
    // ─────────────────────────────────────────────────────────
    public void Write(int row, string column, string value, CellColor color = CellColor.None)
    {
        int col = GetOrCreateColumn(column);
        var cell = _ws.Cell(row, col);
        cell.Value = value;
        if (color != CellColor.None)
            cell.Style.Fill.BackgroundColor = ToXl(color);
    }

    public void ColorRow(int row, CellColor color)
    {
        int last = Math.Max(_ws.Row(row).LastCellUsed()?.Address.ColumnNumber ?? 1,
                            _headers.Count == 0 ? 1 : _headers.Values.Max());
        var range = _ws.Range(row, 1, row, last);
        if (color == CellColor.None) range.Style.Fill.SetBackgroundColor(XLColor.NoColor);
        else range.Style.Fill.BackgroundColor = ToXl(color);
    }

    public void Save()
    {
        try
        {
            _wb.Save();
        }
        catch (IOException ex)
        {
            throw new RprStepException($"Nu pot salva {Path.GetFileName(FilePath)}: fisierul e deschis in alt program. Inchide-l in Excel. ({ex.Message})", ex);
        }
    }

    private static XLColor ToXl(CellColor c) => c switch
    {
        CellColor.Green  => XLColor.FromHtml("#C6EFCE"),
        CellColor.Red    => XLColor.FromHtml("#FFC7CE"),
        CellColor.Yellow => XLColor.FromHtml("#FFEB9C"),
        CellColor.Orange => XLColor.FromHtml("#F8CBAD"),
        CellColor.Blue   => XLColor.FromHtml("#BDD7EE"),
        _                => XLColor.NoColor,
    };

    public void Dispose() => _wb.Dispose();
}
