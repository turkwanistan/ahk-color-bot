Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$left = -1626
$top = 453
$width = -564 - (-1626)
$height = 995 - 453
$bmp = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($left, $top, 0, 0, (New-Object System.Drawing.Size $width, $height))
$bmp.Save('C:\Users\Wanstation\Downloads\ahk\py_wc\shots\runelite.png')
Write-Output "saved $width x $height"
