Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Bitmap]::FromFile('C:\Users\Wanstation\Downloads\ahk\py_wc\shots\runelite.png')

$magenta = @{}
$red = @{}
$green = @{}

for ($y = 0; $y -lt $bmp.Height; $y++) {
    for ($x = 0; $x -lt $bmp.Width; $x++) {
        $p = $bmp.GetPixel($x, $y)
        $r = $p.R; $g = $p.G; $b = $p.B
        # magenta-ish: R and B both high, G low
        if ($r -gt 180 -and $b -gt 180 -and $g -lt 100) {
            $key = "{0:X2}{1:X2}{2:X2}" -f $r,$g,$b
            if (-not $magenta.ContainsKey($key)) { $magenta[$key] = @() }
            if ($magenta[$key].Count -lt 1) { $magenta[$key] += "$x,$y" }
            $magenta[$key] = ,($magenta[$key][0]) + @($magenta[$key].Count)
        }
        # red text-ish: R high, G low, B low
        if ($r -gt 180 -and $g -lt 80 -and $b -lt 80) {
            $key = "{0:X2}{1:X2}{2:X2}" -f $r,$g,$b
            if (-not $red.ContainsKey($key)) { $red[$key] = 0 }
            $red[$key]++
        }
        # bright green-ish (tile highlight)
        if ($g -gt 180 -and $r -lt 100 -and $b -lt 100) {
            $key = "{0:X2}{1:X2}{2:X2}" -f $r,$g,$b
            if (-not $green.ContainsKey($key)) { $green[$key] = 0 }
            $green[$key]++
        }
    }
}

Write-Output "--- magenta candidates (color: firstXY,count) ---"
$magenta.GetEnumerator() | Sort-Object { $_.Value[1] } -Descending | Select-Object -First 5 | ForEach-Object { Write-Output "$($_.Key): $($_.Value[0]) count=$($_.Value[1])" }

Write-Output "--- red candidates (color: count) ---"
$red.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 | ForEach-Object { Write-Output "$($_.Key): $($_.Value)" }

Write-Output "--- green candidates (color: count) ---"
$green.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 | ForEach-Object { Write-Output "$($_.Key): $($_.Value)" }

$bmp.Dispose()
