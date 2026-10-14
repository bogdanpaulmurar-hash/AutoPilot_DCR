// ============================================================
// AutoPilot DC v4 — RPR
// ObjectRepository.cs — Colectia de obiecte marcate cu Spy
// ============================================================

using System.Text.RegularExpressions;

namespace AutoPilotDC.Rpr.Model;

/// <summary>
/// Object Repository: toate elementele marcate, cautate dupa nume.
/// Un repository poate fi folosit de mai multe rutine.
/// </summary>
public sealed class ObjectRepository
{
    public int Version { get; set; } = 1;

    public List<UiObject> Objects { get; set; } = new();

    // 1. Cautare dupa nume (case-insensitive)
    public UiObject? Find(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return null;
        return Objects.FirstOrDefault(o => string.Equals(o.Name, name, StringComparison.OrdinalIgnoreCase));
    }

    // 2. Adauga un obiect nou; daca numele exista, genereaza unul unic (Buton_OK_2)
    public UiObject Add(UiObject obj)
    {
        obj.Name = MakeUniqueName(string.IsNullOrWhiteSpace(obj.Name) ? "Obiect" : obj.Name);
        Objects.Add(obj);
        return obj;
    }

    // 3. Redenumire sigura. Returneaza false daca numele nou e ocupat.
    public bool Rename(UiObject obj, string newName)
    {
        newName = Sanitize(newName);
        if (string.IsNullOrWhiteSpace(newName)) return false;
        var existing = Find(newName);
        if (existing != null && !ReferenceEquals(existing, obj)) return false;
        obj.Name = newName;
        return true;
    }

    public bool Remove(UiObject obj) => Objects.Remove(obj);

    // 4. Nume unic + curat (fara spatii / caractere speciale) — usor de citit in rutine
    public string MakeUniqueName(string baseName)
    {
        baseName = Sanitize(baseName);
        if (string.IsNullOrWhiteSpace(baseName)) baseName = "Obiect";
        if (Find(baseName) == null) return baseName;
        for (int i = 2; ; i++)
        {
            var candidate = $"{baseName}_{i}";
            if (Find(candidate) == null) return candidate;
        }
    }

    public static string Sanitize(string name)
    {
        name = (name ?? "").Trim();
        name = Regex.Replace(name, @"\s+", "_");
        name = Regex.Replace(name, @"[^\p{L}\p{N}_\-\.]", "");
        if (name.Length > 60) name = name[..60];
        return name;
    }
}
