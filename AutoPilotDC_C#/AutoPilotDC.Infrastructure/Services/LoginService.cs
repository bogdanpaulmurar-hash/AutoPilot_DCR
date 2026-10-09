// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// LoginService.cs � Faza 9: Serviciu autentificare Playwright
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

using System;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using AutoPilotDC.Models;
using Microsoft.Playwright;

namespace AutoPilotDC.Infrastructure.Services;

/// <summary>
/// Serviciu de autentificare pentru rutine AutoPilot DC.
/// Suporta: credentials (AES-256), Entra ID SSO, session_reuse.
/// Criptare parola: AES-256-CBC cu key derivat din MachineName + GUID.
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class LoginService
{
    // -- Criptare AES-256 -----------------------------------------
    // Key derivat din MachineName pentru portabilitate per masina
    private static readonly string _machineKey =
        $"AutoPilotDC_{Environment.MachineName}_Siemens_Z003FU5C";

    /// <summary>
    /// Cripteaza o parola plain-text cu AES-256-CBC.
    /// Returneaza Base64(IV + CipherText).
    /// </summary>
    public static string EncryptPassword(string plainText)
    {
        if (string.IsNullOrEmpty(plainText)) return "";

        using var aes = Aes.Create();
        aes.KeySize = 256;
        aes.Mode    = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;
        aes.Key     = DeriveKey(_machineKey);
        aes.GenerateIV();

        using var encryptor = aes.CreateEncryptor();
        var plainBytes  = Encoding.UTF8.GetBytes(plainText);
        var cipherBytes = encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);

        // Concatenam IV + CipherText pentru stocare
        var result = new byte[aes.IV.Length + cipherBytes.Length];
        Buffer.BlockCopy(aes.IV, 0, result, 0, aes.IV.Length);
        Buffer.BlockCopy(cipherBytes, 0, result, aes.IV.Length, cipherBytes.Length);

        return Convert.ToBase64String(result);
    }

    /// <summary>
    /// Decripteaza o parola criptata AES-256-CBC.
    /// Input: Base64(IV + CipherText).
    /// </summary>
    public static string DecryptPassword(string encryptedBase64)
    {
        if (string.IsNullOrEmpty(encryptedBase64)) return "";

        try
        {
            var fullBytes = Convert.FromBase64String(encryptedBase64);

            using var aes = Aes.Create();
            aes.KeySize = 256;
            aes.Mode    = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;
            aes.Key     = DeriveKey(_machineKey);

            // Primii 16 bytes sunt IV
            var iv         = new byte[16];
            var cipherBytes = new byte[fullBytes.Length - 16];
            Buffer.BlockCopy(fullBytes, 0, iv, 0, 16);
            Buffer.BlockCopy(fullBytes, 16, cipherBytes, 0, cipherBytes.Length);

            aes.IV = iv;
            using var decryptor = aes.CreateDecryptor();
            var plainBytes = decryptor.TransformFinalBlock(cipherBytes, 0, cipherBytes.Length);
            return Encoding.UTF8.GetString(plainBytes);
        }
        catch
        {
            return "";
        }
    }

    /// <summary>Deriveaza 32 bytes (256 bit) din string-ul de cheie.</summary>
    private static byte[] DeriveKey(string keyString)
    {
        var data = System.Text.Encoding.UTF8.GetBytes(keyString);
        return SHA256.HashData(data);
    }

    // -- Login principal -------------------------------------------

    /// <summary>
    /// Executa autentificarea pe pagina Playwright conform configuratiei.
    /// Returneaza (true, "") la succes sau (false, mesaj_eroare) la esec.
    /// </summary>
    public async Task<(bool Success, string Error)> ExecuteLoginAsync(
        LoginConfig config, IPage page)
    {
        if (config == null || !config.Enabled || config.Mode == "none")
            return (true, "");

        try
        {
            return config.Mode switch
            {
                "credentials"   => await LoginWithCredentialsAsync(config, page),
                "entra_id"      => await LoginWithEntraIdAsync(config, page),
                "session_reuse" => (true, ""),  // sesiunea e deja activa in profil
                _               => (true, "")
            };
        }
        catch (Exception ex)
        {
            return (false, $"Eroare login: {ex.Message}");
        }
    }

    // -- Credentials mode -----------------------------------------

    private static async Task<(bool Success, string Error)> LoginWithCredentialsAsync(
        LoginConfig config, IPage page)
    {
        var timeout = config.TimeoutSeconds * 1000;

        // Navigare la pagina de login
        if (!string.IsNullOrWhiteSpace(config.LoginUrl))
            await page.GotoAsync(config.LoginUrl,
                new PageGotoOptions { Timeout = timeout, WaitUntil = WaitUntilState.NetworkIdle });

        // Completare username
        if (!string.IsNullOrWhiteSpace(config.UsernameSelector) &&
            !string.IsNullOrWhiteSpace(config.Username))
        {
            await page.WaitForSelectorAsync(config.UsernameSelector,
                new PageWaitForSelectorOptions { Timeout = timeout });
            await page.Locator(config.UsernameSelector).FillAsync(config.Username);
        }

        // Completare parola (decriptata)
        if (!string.IsNullOrWhiteSpace(config.PasswordSelector) &&
            !string.IsNullOrWhiteSpace(config.PasswordEncrypted))
        {
            var plainPassword = DecryptPassword(config.PasswordEncrypted);
            await page.WaitForSelectorAsync(config.PasswordSelector,
                new PageWaitForSelectorOptions { Timeout = timeout });
            await page.Locator(config.PasswordSelector).FillAsync(plainPassword);
        }

        // Submit
        if (!string.IsNullOrWhiteSpace(config.SubmitSelector))
        {
            await page.Locator(config.SubmitSelector).ClickAsync(
                new LocatorClickOptions { Timeout = timeout });
        }

        // Asteapta navigarea post-submit
        await page.WaitForLoadStateAsync(LoadState.NetworkIdle,
            new PageWaitForLoadStateOptions { Timeout = timeout });

        // Verificare succes prin selector
        if (!string.IsNullOrWhiteSpace(config.SuccessSelector))
        {
            try
            {
                await page.WaitForSelectorAsync(config.SuccessSelector,
                    new PageWaitForSelectorOptions { Timeout = timeout });
            }
            catch
            {
                return (false, $"Login esuat: selectorul de succes '{config.SuccessSelector}' nu a fost gasit.");
            }
        }

        return (true, "");
    }

    // -- Entra ID mode ---------------------------------------------

    private static async Task<(bool Success, string Error)> LoginWithEntraIdAsync(
        LoginConfig config, IPage page)
    {
        var timeout = config.TimeoutSeconds * 1000;

        // Navigare la URL (poate fi URL-ul aplicatiei care redirecteaza la Entra ID)
        if (!string.IsNullOrWhiteSpace(config.LoginUrl))
            await page.GotoAsync(config.LoginUrl,
                new PageGotoOptions { Timeout = timeout, WaitUntil = WaitUntilState.NetworkIdle });

        // Detectare automata Entra ID: verifica URL-ul curent
        var currentUrl = page.Url;
        bool isEntraPage = currentUrl.Contains("login.microsoftonline.com") ||
                           currentUrl.Contains("microsoftonline.com");

        if (isEntraPage)
        {
            // Completare email/UPN daca e disponibil
            if (!string.IsNullOrWhiteSpace(config.Username))
            {
                try
                {
                    await page.WaitForSelectorAsync("input[type='email']",
                        new PageWaitForSelectorOptions { Timeout = 5000 });
                    await page.Locator("input[type='email']").FillAsync(config.Username);
                    await page.Locator("input[type='submit']").ClickAsync();
                    await page.WaitForLoadStateAsync(LoadState.NetworkIdle,
                        new PageWaitForLoadStateOptions { Timeout = timeout });
                }
                catch { /* SSO poate sari peste ecranul de email */ }
            }

            // Asteapta redirectul post-SSO (max TimeoutSeconds)
            try
            {
                await page.WaitForURLAsync(url => !url.Contains("microsoftonline.com"),
                    new PageWaitForURLOptions { Timeout = timeout });
            }
            catch
            {
                return (false, "Timeout Entra ID SSO � autentificarea nu s-a finalizat in timp util.");
            }
        }

        // Verificare selector succes
        if (!string.IsNullOrWhiteSpace(config.SuccessSelector))
        {
            try
            {
                await page.WaitForSelectorAsync(config.SuccessSelector,
                    new PageWaitForSelectorOptions { Timeout = timeout });
            }
            catch
            {
                return (false, $"Login Entra ID esuat: selectorul '{config.SuccessSelector}' nu a fost gasit.");
            }
        }

        return (true, "");
    }
}
