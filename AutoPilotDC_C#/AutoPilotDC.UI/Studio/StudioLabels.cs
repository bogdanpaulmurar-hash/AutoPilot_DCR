// ============================================================
// AutoPilot DC v4 — Studio RPR
// StudioLabels.cs — Textele in romana pentru dropdown-uri + iconite
// ============================================================

using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.UI.Studio;

public static class StudioLabels
{
    public static readonly (ErrorPolicy Value, string Label)[] ErrorPolicies =
    {
        (ErrorPolicy.Inherit,  "Ca setarea rutinei"),
        (ErrorPolicy.Ask,      "Intreaba-ma (Reincearca / Sari / Opreste)"),
        (ErrorPolicy.Stop,     "Opreste rutina"),
        (ErrorPolicy.Continue, "Continua (doar logheaza)"),
        (ErrorPolicy.SkipRow,  "Sari la urmatorul rand Excel"),
    };

    public static readonly (ConditionKind Value, string Label)[] ConditionKinds =
    {
        (ConditionKind.ElementExists,    "Obiectul exista pe ecran"),
        (ConditionKind.ElementNotExists, "Obiectul NU exista / a disparut"),
        (ConditionKind.ElementVisible,   "Obiectul e vizibil"),
        (ConditionKind.ElementEnabled,   "Obiectul e activ (poate fi apasat)"),
        (ConditionKind.ElementText,      "Textul obiectului ..."),
        (ConditionKind.Compare,          "Compara doua valori / variabile"),
        (ConditionKind.AllOf,            "Toate conditiile de mai jos (SI)"),
        (ConditionKind.AnyOf,            "Oricare din conditiile de mai jos (SAU)"),
    };

    public static readonly (CompareOperator Value, string Label)[] Operators =
    {
        (CompareOperator.Equals,         "este egal cu"),
        (CompareOperator.NotEquals,      "este diferit de"),
        (CompareOperator.Contains,       "contine"),
        (CompareOperator.NotContains,    "nu contine"),
        (CompareOperator.StartsWith,     "incepe cu"),
        (CompareOperator.EndsWith,       "se termina cu"),
        (CompareOperator.IsEmpty,        "este gol"),
        (CompareOperator.IsNotEmpty,     "nu este gol"),
        (CompareOperator.GreaterThan,    "este mai mare decat"),
        (CompareOperator.GreaterOrEqual, "este mai mare sau egal cu"),
        (CompareOperator.LessThan,       "este mai mic decat"),
        (CompareOperator.LessOrEqual,    "este mai mic sau egal cu"),
        (CompareOperator.MatchesRegex,   "se potriveste cu expresia (regex)"),
    };

    public static readonly (UiTechnology Value, string Label)[] Technologies =
    {
        (UiTechnology.Web,         "Web (Playwright)"),
        (UiTechnology.WebSelenium, "Web (Selenium)"),
        (UiTechnology.Sap,         "SAP GUI"),
        (UiTechnology.Desktop,     "Aplicatie desktop"),
    };

    public static readonly (WaitMode Value, string Label)[] WaitModes =
    {
        (WaitMode.Seconds,  "Un numar de secunde"),
        (WaitMode.UntilTrue, "Pana cand o conditie e adevarata"),
    };

    public static readonly (LoopMode Value, string Label)[] LoopModes =
    {
        (LoopMode.Times, "De un numar de ori"),
        (LoopMode.While, "Cat timp conditia e adevarata (verifica inainte)"),
        (LoopMode.Until, "Pana cand conditia devine adevarata (verifica dupa)"),
    };

    public static readonly (VariableOperation Value, string Label)[] VariableOperations =
    {
        (VariableOperation.Set,       "Seteaza valoarea"),
        (VariableOperation.Append,    "Adauga la final"),
        (VariableOperation.Increment, "Creste cu (implicit 1)"),
        (VariableOperation.Decrement, "Scade cu (implicit 1)"),
        (VariableOperation.Trim,      "Sterge spatiile de la capete"),
        (VariableOperation.ToUpper,   "LITERE MARI"),
        (VariableOperation.ToLower,   "litere mici"),
        (VariableOperation.Replace,   "Inlocuieste text"),
    };

    public static readonly (CellColor Value, string Label)[] CellColors =
    {
        (CellColor.None,   "Fara culoare"),
        (CellColor.Green,  "Verde (OK)"),
        (CellColor.Red,    "Rosu (eroare)"),
        (CellColor.Yellow, "Galben (atentie)"),
        (CellColor.Orange, "Portocaliu"),
        (CellColor.Blue,   "Albastru"),
    };

    public static readonly (RprLogLevel Value, string Label)[] LogLevels =
    {
        (RprLogLevel.Info,    "Informatie"),
        (RprLogLevel.Warning, "Atentionare"),
        (RprLogLevel.Error,   "Eroare"),
    };

    public static string IconFor(RprNode node) => node switch
    {
        ActionNode a => a.Action switch
        {
            RprAction.OpenBrowser or RprAction.Navigate or RprAction.Back or RprAction.Refresh
                or RprAction.SwitchTab or RprAction.CloseBrowser or RprAction.HandleDialog or RprAction.ScreenshotPage => "🌐",
            RprAction.SapConnect or RprAction.SapTransaction or RprAction.SapSendKey
                or RprAction.SapReadStatusBar or RprAction.SapGridReadCell or RprAction.SapGridRowCount => "🟦",
            RprAction.LaunchApp or RprAction.AttachWindow or RprAction.CloseWindow => "🖥",
            RprAction.TypeText or RprAction.AppendText or RprAction.Clear => "⌨",
            RprAction.ReadText or RprAction.ReadValue or RprAction.ReadAttribute => "👁",
            _ => "👆",
        },
        WaitNode        => "⏱",
        SetVariableNode => "✎",
        IfNode          => "🔀",
        LoopNode        => "🔁",
        ForEachRowNode  => "📊",
        WriteExcelNode  => "📝",
        QuestionNode    => "💬",
        TryNode         => "🛡",
        GroupNode       => "📁",
        LogNode         => "🗒",
        BreakNode       => "⏏",
        StopNode        => "⛔",
        LegacyStepNode  => "🖱",
        _               => "•",
    };
}
