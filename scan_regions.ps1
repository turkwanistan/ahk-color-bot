Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Bitmap]::FromFile('C:\Users\Wanstation\Downloads\ahk\py_wc\shots\runelite.png')

$redRows = @{}
$magentaLeft = New-Object System.Collections.Generic.List[string]
$magentaRight = New-Object System.Collections.Generic.List[string]

for ($y = 0; $y -lt $bmp.Height; $y++) {
    for ($x = 0; $x -lt $bmp.Width; $x++) {
        $p = $bmp.GetPixel($x, $y)
        $r = $p.R; $g = $p.G; $b = $p.B
        if ($r -gt 200 -and $g -lt 40 -and $b -lt 40) {
            $band = [Math]::Floor($y / 5) * 5
            if (-not $redRows.ContainsKey($band)) { $redRows[$band] = 0 }
            $redRows[$band]++
        }
        if ($r -gt 220 -and $b -gt 220 -and $g -lt 40) {
            if ($x -lt 540) { $magentaLeft.Add("$x,$y") } else { $magentaRight.Add("$x,$y") }
        }
    }
}

Write-Output "--- red pixel rows (y-band: count) ---"
$redRows.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output "$($_.Name): $($_.Value)" }

Write-Output "--- magenta LEFT (viewport) bounding box, n=$($magentaLeft.Count) ---"
if ($magentaLeft.Count -gt 0) {
    $xs = $magentaLeft | ForEach-Object { [int]($_.Split(',')[0]) }
    $ys = $magentaLeft | ForEach-Object { [int]($_.Split(',')[1]) }
    Write-Output "x: $($xs | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Minimum) - $($xs | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Maximum)"
    Write-Output "y: $($ys | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Minimum) - $($ys | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Maximum)"
}

Write-Output "--- magenta RIGHT (inventory?) bounding box, n=$($magentaRight.Count) ---"
if ($magentaRight.Count -gt 0) {
    $xs2 = $magentaRight | ForEach-Object { [int]($_.Split(',')[0]) }
    $ys2 = $magentaRight | ForEach-Object { [int]($_.Split(',')[1]) }
    Write-Output "x: $($xs2 | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Minimum) - $($xs2 | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Maximum)"
    Write-Output "y: $($ys2 | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Minimum) - $($ys2 | Measure-Object -Minimum -Maximum | Select-Object -ExpandProperty Maximum)"
}

$bmp.Dispose()
