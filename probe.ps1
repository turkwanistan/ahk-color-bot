Add-Type -AssemblyName System.Windows.Forms
foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
    Write-Output "$($s.DeviceName) Primary=$($s.Primary) Bounds=$($s.Bounds)"
}
Write-Output '---'
Add-Type -AssemblyName System.Windows.Forms
$p = Get-Process -Name RuneLite
Write-Output "PID=$($p.Id) Title=$($p.MainWindowTitle)"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@
$rect = New-Object Win32+RECT
[Win32]::GetWindowRect($p.MainWindowHandle, [ref]$rect) | Out-Null
Write-Output "WindowRect Left=$($rect.Left) Top=$($rect.Top) Right=$($rect.Right) Bottom=$($rect.Bottom)"
