# Fix double-UTF8 encoding in XAML and CS files
# Pattern: file was UTF8 bytes read as Windows-1252, then re-saved as UTF8
# Fix: re-read as UTF8, re-encode bytes as Windows-1252, then decode as UTF8

Set-Location $PSScriptRoot

$files = Get-ChildItem -Recurse -Include "*.xaml","*.cs" | Where-Object {
	$_.FullName -notmatch "\\(bin|obj)\\"
}

foreach ($file in $files) {
	try {
		$text    = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
		$bytes   = [System.Text.Encoding]::GetEncoding(1252).GetBytes($text)
		$fixed   = [System.Text.Encoding]::UTF8.GetString($bytes)
		if ($fixed -ne $text) {
			[System.IO.File]::WriteAllText($file.FullName, $fixed, [System.Text.Encoding]::UTF8)
			Write-Host "Fixed: $($file.Name)"
		}
	} catch {
		Write-Warning "Skip $($file.Name): $_"
	}
}
Write-Host "`nDone!"
