Add-Type -AssemblyName System.Drawing

$iconsDir = "C:\Users\DURHAM\claude projects\dry-run\icons"
New-Item -ItemType Directory -Force -Path $iconsDir | Out-Null

$bg = [System.Drawing.Color]::FromArgb(255, 0x30, 0xD6, 0x8A)   # emerald #30d68a
$fg = [System.Drawing.Color]::FromArgb(255, 0x0A, 0x0A, 0x0A)   # near-black checkmark

function New-IconPng {
    param(
        [int]$Size,
        [string]$Path
    )

    $bmp = New-Object System.Drawing.Bitmap($Size, $Size)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    # Full-bleed emerald background (iOS/Android apply their own corner mask)
    $g.Clear($bg)

    $s = $Size / 512.0

    $pen = New-Object System.Drawing.Pen($fg, [float](50 * $s))
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round

    $pts = @(
        (New-Object System.Drawing.PointF([float](146 * $s), [float](274 * $s))),
        (New-Object System.Drawing.PointF([float](224 * $s), [float](352 * $s))),
        (New-Object System.Drawing.PointF([float](390 * $s), [float](176 * $s)))
    )
    $g.DrawLines($pen, $pts)

    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)

    $pen.Dispose()
    $g.Dispose()
    $bmp.Dispose()
}

New-IconPng -Size 512 -Path "$iconsDir\icon-512.png"
New-IconPng -Size 192 -Path "$iconsDir\icon-192.png"
New-IconPng -Size 180 -Path "$iconsDir\apple-touch-icon.png"
New-IconPng -Size 32  -Path "$iconsDir\favicon-32.png"

Get-ChildItem $iconsDir | Select-Object Name, Length
