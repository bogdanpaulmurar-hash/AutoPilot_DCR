// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// ILoginService.cs � Interfata pentru serviciul de login (Faza 9)
// IMPORTANT: Core nu referencieaza Playwright � IPage eliminat din interfata
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using System.Threading.Tasks;
using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Interfata pentru executia login-ului automat inainte de rularea rutinei.
/// Implementarea concreta (LoginService) se afla in AutoPilotDC.Infrastructure.
/// </summary>
public interface ILoginService
{
    /// <summary>
    /// Executa login-ul conform configuratiei.
    /// page este transmis ca object pentru a evita dependenta de Microsoft.Playwright in Core.
    /// Cast la IPage se face in implementare (LoginService).
    /// </summary>
    Task<(bool Success, string Error)> ExecuteLoginAsync(LoginConfig config, object page);

    /// <summary>
    /// Verifica daca login-ul este configurat si activ.
    /// </summary>
    bool IsEnabled(LoginConfig? config);
}