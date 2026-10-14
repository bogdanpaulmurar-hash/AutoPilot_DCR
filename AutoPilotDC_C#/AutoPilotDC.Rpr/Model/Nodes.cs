// ============================================================
// AutoPilot DC v4 — RPR
// Nodes.cs — Pasii unei rutine, organizati ca arbore.
// Fiecare tip de nod = un bloc din Toolbox-ul Studio.
// Serializare JSON polimorfica: campul "kind" spune tipul.
// ============================================================

using System.Text.Json.Serialization;
using AutoPilotDC.Models;

namespace AutoPilotDC.Rpr.Model;

/// <summary>Ce face motorul cand un pas esueaza.</summary>
public enum ErrorPolicy
{
    /// <summary>Foloseste politica globala a rularii.</summary>
    Inherit,
    /// <summary>Opreste rutina.</summary>
    Stop,
    /// <summary>Intreaba utilizatorul (Reincearca / Sari / Opreste).</summary>
    Ask,
    /// <summary>Logheaza eroarea si continua.</summary>
    Continue,
    /// <summary>Sari la urmatorul rand din Excel (in "Pentru fiecare rand").</summary>
    SkipRow,
}

// ─────────────────────────────────────────────────────────────
// Baza
// ─────────────────────────────────────────────────────────────

[JsonPolymorphic(TypeDiscriminatorPropertyName = "kind")]
[JsonDerivedType(typeof(ActionNode),      "action")]
[JsonDerivedType(typeof(WaitNode),        "wait")]
[JsonDerivedType(typeof(SetVariableNode), "set_variable")]
[JsonDerivedType(typeof(IfNode),          "if")]
[JsonDerivedType(typeof(LoopNode),        "loop")]
[JsonDerivedType(typeof(ForEachRowNode),  "for_each_row")]
[JsonDerivedType(typeof(WriteExcelNode),  "write_excel")]
[JsonDerivedType(typeof(QuestionNode),    "question")]
[JsonDerivedType(typeof(TryNode),         "try")]
[JsonDerivedType(typeof(GroupNode),       "group")]
[JsonDerivedType(typeof(LogNode),         "log")]
[JsonDerivedType(typeof(BreakNode),       "break")]
[JsonDerivedType(typeof(StopNode),        "stop")]
[JsonDerivedType(typeof(LegacyStepNode),  "legacy_step")]
public abstract class RprNode
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..10];

    /// <summary>Titlu ales de utilizator. Gol = titlu generat automat.</summary>
    public string Label { get; set; } = "";

    /// <summary>Pas dezactivat = sarit la rulare (echivalent "Omite pas").</summary>
    public bool Enabled { get; set; } = true;

    public int DelayBeforeMs { get; set; }
    public int DelayAfterMs { get; set; }

    public ErrorPolicy OnError { get; set; } = ErrorPolicy.Inherit;

    public string Comment { get; set; } = "";

    /// <summary>Textul afisat in arborele rutinei.</summary>
    [JsonIgnore]
    public string Title => string.IsNullOrWhiteSpace(Label) ? AutoTitle() : Label;

    /// <summary>Titlu generat din configurare.</summary>
    public abstract string AutoTitle();

    /// <summary>Numele tipului de bloc (afisat in Studio).</summary>
    [JsonIgnore]
    public abstract string KindLabel { get; }
}

/// <summary>Nod care contine alti pasi (Daca, Repeta, Pentru fiecare rand...).</summary>
public interface IContainerNode
{
    /// <summary>Ramurile nodului: (nume ramura, lista de pasi).</summary>
    IEnumerable<(string, List<RprNode>)> Branches { get; }
}

// ─────────────────────────────────────────────────────────────
// Actiune pe obiect / browser / SAP / desktop
// ─────────────────────────────────────────────────────────────

public sealed class ActionNode : RprNode
{
    public RprAction Action { get; set; } = RprAction.Click;

    /// <summary>Numele obiectului din Object Repository.</summary>
    public string Target { get; set; } = "";

    /// <summary>Valoarea actiunii (text, URL, tasta...). Accepta variabile: {Rand.IBase}.</summary>
    public string Value { get; set; } = "";

    /// <summary>Variabila in care se salveaza rezultatul (pentru Citeste...).</summary>
    public string OutputVariable { get; set; } = "";

    /// <summary>Tehnologia pentru actiuni fara obiect (Deschide browser, SAP...).</summary>
    public UiTechnology Technology { get; set; } = UiTechnology.Web;

    /// <summary>Cat asteptam elementul sa apara (ms).</summary>
    public int TimeoutMs { get; set; } = 10000;

    /// <summary>Executa direct pe element (fara miscarea vizibila a mouse-ului), unde e posibil.</summary>
    public bool DirectMode { get; set; }

    public override string KindLabel => "Actiune";

    public override string AutoTitle()
    {
        var info = ActionCatalog.Get(Action);
        var s = info.Label;
        if (!string.IsNullOrWhiteSpace(Target)) s += $" [{Target}]";
        if (info.ValueLabel != null && !string.IsNullOrWhiteSpace(Value)) s += $" = \"{Value}\"";
        if (info.ProducesOutput && !string.IsNullOrWhiteSpace(OutputVariable)) s += $" → {{{OutputVariable}}}";
        return s;
    }
}

// ─────────────────────────────────────────────────────────────
// Asteptare (fix sau pana cand o conditie e adevarata)
// ─────────────────────────────────────────────────────────────

public enum WaitMode { Seconds, UntilTrue }

public sealed class WaitNode : RprNode
{
    public WaitMode Mode { get; set; } = WaitMode.Seconds;
    public double Seconds { get; set; } = 1;
    public Condition Condition { get; set; } = new();
    public int TimeoutMs { get; set; } = 30000;

    /// <summary>Daca conditia nu devine adevarata in timp: eroare (true) sau continua (false).</summary>
    public bool FailOnTimeout { get; set; } = true;

    public override string KindLabel => "Asteapta";
    public override string AutoTitle() => Mode == WaitMode.Seconds
        ? $"Asteapta {Seconds:0.##} s"
        : $"Asteapta pana cand {Condition.Describe()} (max {TimeoutMs / 1000.0:0.#} s)";
}

// ─────────────────────────────────────────────────────────────
// Variabile
// ─────────────────────────────────────────────────────────────

public enum VariableOperation { Set, Append, Increment, Decrement, Trim, ToUpper, ToLower, Replace }

public sealed class SetVariableNode : RprNode
{
    public string Name { get; set; } = "Var1";
    public VariableOperation Operation { get; set; } = VariableOperation.Set;
    public string Value { get; set; } = "";

    /// <summary>Pentru Replace: textul cautat (Value = inlocuire).</summary>
    public string Find { get; set; } = "";

    public override string KindLabel => "Variabila";
    public override string AutoTitle() => Operation switch
    {
        VariableOperation.Set       => $"{{{Name}}} = \"{Value}\"",
        VariableOperation.Append    => $"{{{Name}}} += \"{Value}\"",
        VariableOperation.Increment => $"{{{Name}}} + 1",
        VariableOperation.Decrement => $"{{{Name}}} - 1",
        VariableOperation.Replace   => $"{{{Name}}}: \"{Find}\" → \"{Value}\"",
        _                           => $"{{{Name}}}: {Operation}",
    };
}

// ─────────────────────────────────────────────────────────────
// Daca / Altfel
// ─────────────────────────────────────────────────────────────

public sealed class IfNode : RprNode, IContainerNode
{
    public Condition Condition { get; set; } = new();
    public List<RprNode> Then { get; set; } = new();
    public List<RprNode> Else { get; set; } = new();

    public override string KindLabel => "Daca";
    public override string AutoTitle() => $"Daca {Condition.Describe()}";

    [JsonIgnore]
    public IEnumerable<(string, List<RprNode>)> Branches
    {
        get { yield return ("Atunci", Then); yield return ("Altfel", Else); }
    }
}

// ─────────────────────────────────────────────────────────────
// Repeta
// ─────────────────────────────────────────────────────────────

public enum LoopMode { Times, While, Until }

public sealed class LoopNode : RprNode, IContainerNode
{
    public LoopMode Mode { get; set; } = LoopMode.Times;

    /// <summary>De cate ori (Times). Accepta variabile ca text: "{NrRepetari}".</summary>
    public string Count { get; set; } = "3";

    public Condition Condition { get; set; } = new();

    /// <summary>Protectie anti-bucla-infinita pentru While/Until.</summary>
    public int MaxIterations { get; set; } = 1000;

    /// <summary>Variabila cu numarul repetarii curente (1, 2, 3...).</summary>
    public string CounterVariable { get; set; } = "Repetare";

    public List<RprNode> Body { get; set; } = new();

    public override string KindLabel => "Repeta";
    public override string AutoTitle() => Mode switch
    {
        LoopMode.Times => $"Repeta de {Count} ori",
        LoopMode.While => $"Repeta cat timp {Condition.Describe()}",
        _              => $"Repeta pana cand {Condition.Describe()}",
    };

    [JsonIgnore]
    public IEnumerable<(string, List<RprNode>)> Branches { get { yield return ("Pasi", Body); } }
}

// ─────────────────────────────────────────────────────────────
// Pentru fiecare rand din Excel
// ─────────────────────────────────────────────────────────────

public sealed class ForEachRowNode : RprNode, IContainerNode
{
    /// <summary>Calea fisierului .xlsx (accepta variabile).</summary>
    public string FilePath { get; set; } = "";

    /// <summary>Foaia (gol = prima foaie).</summary>
    public string Sheet { get; set; } = "";

    /// <summary>Randul cu titlurile coloanelor (0 = fara titluri, coloanele se numesc A, B, C...).</summary>
    public int HeaderRow { get; set; } = 1;

    /// <summary>Primul rand cu date. 0 = imediat dupa HeaderRow.</summary>
    public int StartRow { get; set; }

    /// <summary>Ultimul rand. 0 = pana la primul rand gol in coloana cheie.</summary>
    public int EndRow { get; set; }

    /// <summary>Coloana care decide sfarsitul datelor (titlu sau litera). Gol = prima coloana.</summary>
    public string KeyColumn { get; set; } = "";

    /// <summary>Prefixul variabilelor de rand: {Rand.IBase}, {Rand.A}, {Rand.#} (numarul randului).</summary>
    public string RowVariable { get; set; } = "Rand";

    /// <summary>Coloana in care se scrie automat OK / EROARE + mesaj (gol = nu se scrie).</summary>
    public string StatusColumn { get; set; } = "Status";

    /// <summary>Coloreaza randul: verde la succes, rosu la eroare.</summary>
    public bool ColorRows { get; set; } = true;

    /// <summary>Salveaza fisierul dupa fiecare rand (sigur la intreruperi).</summary>
    public bool SaveAfterEachRow { get; set; } = true;

    /// <summary>Sari peste randurile deja marcate OK in coloana de status (reluare dupa oprire).</summary>
    public bool SkipCompletedRows { get; set; } = true;

    public List<RprNode> Body { get; set; } = new();

    public override string KindLabel => "Pentru fiecare rand Excel";
    public override string AutoTitle()
    {
        var file = string.IsNullOrWhiteSpace(FilePath) ? "(alege fisier)" : Path.GetFileName(FilePath);
        var sheet = string.IsNullOrWhiteSpace(Sheet) ? "" : $" / {Sheet}";
        return $"Pentru fiecare rand din {file}{sheet} → {{{RowVariable}.*}}";
    }

    [JsonIgnore]
    public IEnumerable<(string, List<RprNode>)> Branches { get { yield return ("Pasi pentru fiecare rand", Body); } }
}

public enum CellColor { None, Green, Red, Yellow, Orange, Blue }

/// <summary>Scrie o valoare in randul curent din Excel (in interiorul "Pentru fiecare rand").</summary>
public sealed class WriteExcelNode : RprNode
{
    /// <summary>Coloana: titlul (ex: "Rezultat") sau litera (ex: "D"). Coloana noua se creeaza automat.</summary>
    public string Column { get; set; } = "Rezultat";

    public string Value { get; set; } = "";

    public CellColor Color { get; set; } = CellColor.None;

    public override string KindLabel => "Scrie in Excel";
    public override string AutoTitle() => $"Excel [{Column}] = \"{Value}\"";
}

// ─────────────────────────────────────────────────────────────
// Intrebare catre utilizator
// ─────────────────────────────────────────────────────────────

public sealed class QuestionNode : RprNode
{
    public string Text { get; set; } = "Continui?";

    /// <summary>Butoane separate prin virgula.</summary>
    public string Buttons { get; set; } = "Continua,Opreste,Sari";

    /// <summary>Raspunsul ales se salveaza aici (poate fi folosit apoi in Daca).</summary>
    public string OutputVariable { get; set; } = "Raspuns";

    /// <summary>Butonul care opreste rutina.</summary>
    public string StopButton { get; set; } = "Opreste";

    /// <summary>Butonul care sare la urmatorul rand din Excel.</summary>
    public string SkipButton { get; set; } = "Sari";

    public override string KindLabel => "Intrebare";
    public override string AutoTitle() => $"Intreaba: \"{Text}\" [{Buttons}]";
}

// ─────────────────────────────────────────────────────────────
// Incearca / La eroare
// ─────────────────────────────────────────────────────────────

public sealed class TryNode : RprNode, IContainerNode
{
    public List<RprNode> Body { get; set; } = new();
    public List<RprNode> Catch { get; set; } = new();

    /// <summary>Mesajul erorii prinse se salveaza aici.</summary>
    public string ErrorVariable { get; set; } = "Eroare";

    public override string KindLabel => "Incearca";
    public override string AutoTitle() => $"Incearca (eroarea → {{{ErrorVariable}}})";

    [JsonIgnore]
    public IEnumerable<(string, List<RprNode>)> Branches
    {
        get { yield return ("Incearca", Body); yield return ("La eroare", Catch); }
    }
}

/// <summary>Grup de pasi (doar pentru organizare).</summary>
public sealed class GroupNode : RprNode, IContainerNode
{
    public List<RprNode> Body { get; set; } = new();
    public override string KindLabel => "Grup";
    public override string AutoTitle() => "Grup";

    [JsonIgnore]
    public IEnumerable<(string, List<RprNode>)> Branches { get { yield return ("Pasi", Body); } }
}

public enum RprLogLevel { Info, Warning, Error }

public sealed class LogNode : RprNode
{
    public string Message { get; set; } = "";
    public RprLogLevel Level { get; set; } = RprLogLevel.Info;
    public override string KindLabel => "Log";
    public override string AutoTitle() => $"Log: \"{Message}\"";
}

/// <summary>Iese din cea mai apropiata bucla (Repeta / Pentru fiecare rand).</summary>
public sealed class BreakNode : RprNode
{
    /// <summary>true = treci la urmatoarea iteratie (continue); false = iesi din bucla (break).</summary>
    public bool NextIteration { get; set; }
    public override string KindLabel => "Iesi din bucla";
    public override string AutoTitle() => NextIteration ? "Treci la urmatoarea repetare" : "Iesi din bucla";
}

/// <summary>Opreste rutina (cu succes sau cu eroare).</summary>
public sealed class StopNode : RprNode
{
    public string Message { get; set; } = "";
    public bool AsError { get; set; }
    public override string KindLabel => "Opreste rutina";
    public override string AutoTitle() => AsError ? $"Opreste cu eroare: \"{Message}\"" : "Opreste rutina";
}

/// <summary>
/// Pas din rutinele vechi (v3.9, pe coordonate). Pastrat pentru compatibilitate;
/// se executa prin motorul desktop vechi (DesktopEngine).
/// </summary>
public sealed class LegacyStepNode : RprNode
{
    public StepModel Step { get; set; } = new();
    public override string KindLabel => "Pas vechi (coordonate)";
    public override string AutoTitle() => $"[v3.9] {Step.GetDisplayType()} ({Step.X},{Step.Y}) {Step.Description}".Trim();
}
