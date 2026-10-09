using System;
using System.Collections.Generic;
using ClosedXML.Excel;

namespace AutoPilotDC.Infrastructure.Services
{
    /// <summary>
    /// Integrare Excel via ClosedXML (inlocuieste openpyxl din Python).
    /// Suporta: load data din range, write result, cell styling (PatternFill + Font + Alignment).
    /// </summary>
    public class ExcelEngine
    {
        private IXLWorkbook? _workbook;
        private string?      _filePath;

        public bool LoadFile(string path)
        {
            try { _workbook = new XLWorkbook(path); _filePath = path; return true; }
            catch (Exception ex) { Console.WriteLine($"[Excel] Load failed: {ex.Message}"); return false; }
        }

        public List<List<string>> ReadRange(string rangeAddress, string? sheetName = null)
        {
            var result = new List<List<string>>();
            if (_workbook == null) return result;
            try
            {
                var sheet = sheetName != null ? _workbook.Worksheet(sheetName) : _workbook.Worksheet(1);
                foreach (var row in sheet.Range(rangeAddress).Rows())
                {
                    var rd = new List<string>();
                    foreach (var cell in row.Cells()) rd.Add(cell.GetString());
                    result.Add(rd);
                }
            }
            catch (Exception ex) { Console.WriteLine($"[Excel] ReadRange failed: {ex.Message}"); }
            return result;
        }

        public bool WriteCell(string cellAddress, object value, string? sheetName = null)
        {
            if (_workbook == null) return false;
            try
            {
                var sheet = sheetName != null ? _workbook.Worksheet(sheetName) : _workbook.Worksheet(1);
                sheet.Cell(cellAddress).Value = XLCellValue.FromObject(value);
                return true;
            }
            catch (Exception ex) { Console.WriteLine($"[Excel] WriteCell failed: {ex.Message}"); return false; }
        }

        public bool WriteResult(string cellAddress, object value,
            string? bgColor = null, bool bold = false, string? sheetName = null)
        {
            if (!WriteCell(cellAddress, value, sheetName)) return false;
            try
            {
                var sheet = sheetName != null ? _workbook!.Worksheet(sheetName) : _workbook!.Worksheet(1);
                var cell = sheet.Cell(cellAddress);
                if (!string.IsNullOrEmpty(bgColor))
                    cell.Style.Fill.BackgroundColor = XLColor.FromHtml(bgColor);
                if (bold) cell.Style.Font.Bold = true;
                return true;
            }
            catch (Exception ex) { Console.WriteLine($"[Excel] Styling failed: {ex.Message}"); return false; }
        }

        public bool Save(string? path = null)
        {
            if (_workbook == null) return false;
            try { _workbook.SaveAs(path ?? _filePath ?? throw new InvalidOperationException("No path.")); return true; }
            catch (Exception ex) { Console.WriteLine($"[Excel] Save failed: {ex.Message}"); return false; }
        }

        public IEnumerable<string> GetSheetNames()
        {
            if (_workbook == null) yield break;
            foreach (var ws in _workbook.Worksheets) yield return ws.Name;
        }

        public void Close() { _workbook?.Dispose(); _workbook = null; _filePath = null; }
    }
}