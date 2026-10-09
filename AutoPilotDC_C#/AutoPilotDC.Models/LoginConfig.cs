// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// LoginConfig.cs � Faza 9: Model configurare login per rutina
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Models;

/// <summary>
/// Configurare autentificare optionala per rutina.
/// Suporta 4 moduri: none, credentials, entra_id, session_reuse.
/// Parola este stocata criptat AES-256 (key derivat din machine GUID).
/// </summary>
public class LoginConfig
{
    /// <summary>Activare login inainte de rularea rutinei.</summary>
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = false;

    /// <summary>
    /// Modul de autentificare:
    /// "none"          - fara autentificare (skip)
    /// "credentials"   - URL + Username + Parola criptata AES-256
    /// "entra_id"      - Microsoft Entra ID (Azure AD SSO)
    /// "session_reuse" - reutilizeaza sesiunea din profilul browser
    /// </summary>
    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "none";

    // -- Credentials mode ------------------------------------------
    [JsonPropertyName("login_url")]
    public string LoginUrl { get; set; } = "";

    [JsonPropertyName("username")]
    public string Username { get; set; } = "";

    /// <summary>Parola criptata AES-256 (Base64). NU stoca plain text!</summary>
    [JsonPropertyName("password_encrypted")]
    public string PasswordEncrypted { get; set; } = "";

    [JsonPropertyName("username_selector")]
    public string UsernameSelector { get; set; } = "#username";

    [JsonPropertyName("password_selector")]
    public string PasswordSelector { get; set; } = "#password";

    [JsonPropertyName("submit_selector")]
    public string SubmitSelector { get; set; } = "button[type='submit']";

    /// <summary>Selector CSS/XPath pentru verificare succes login.</summary>
    [JsonPropertyName("success_selector")]
    public string SuccessSelector { get; set; } = "";

    // -- Entra ID mode ---------------------------------------------
    [JsonPropertyName("entra_id_tenant_id")]
    public string EntraIdTenantId { get; set; } = "";

    [JsonPropertyName("entra_id_client_id")]
    public string EntraIdClientId { get; set; } = "";

    // -- Session reuse mode ----------------------------------------
    [JsonPropertyName("reuse_existing_session")]
    public bool ReuseExistingSession { get; set; } = false;

    [JsonPropertyName("browser_profile_path")]
    public string BrowserProfilePath { get; set; } = "";

    // -- Timeout ---------------------------------------------------
    [JsonPropertyName("timeout_seconds")]
    public int TimeoutSeconds { get; set; } = 30;
}
