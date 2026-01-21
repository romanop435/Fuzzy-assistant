$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$addData = @("config;config")
if (Test-Path (Join-Path $root "models")) {
    $addData += "models;models"
}
if (Test-Path (Join-Path $root "assets")) {
    $addData += "assets;assets"
}
$iconPath = Join-Path $root "assets\\logo-fuzzy.ico"
$pngIconPath = Join-Path $root "assets\\logo-fuzzy.png"
if (-not (Test-Path $iconPath) -and (Test-Path $pngIconPath)) {
    try {
        Add-Type -AssemblyName System.Drawing
        $png = [System.Drawing.Image]::FromFile($pngIconPath)
        $bmp = New-Object System.Drawing.Bitmap $png, 256, 256
        $icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
        $stream = New-Object System.IO.FileStream($iconPath, [System.IO.FileMode]::Create)
        $icon.Save($stream)
        $stream.Close()
        $icon.Dispose()
        $bmp.Dispose()
        $png.Dispose()
    } catch {
        Write-Host "Icon conversion failed: $($_.Exception.Message)"
    }
}
$addArgs = @()
foreach ($item in $addData) {
    $addArgs += "--add-data"
    $addArgs += $item
}
if (Test-Path $iconPath) {
    $addArgs += "--icon"
    $addArgs += $iconPath
}
python -m PyInstaller --noconsole --onefile --name FaziAssistant --collect-all vosk @addArgs "app\\main.py"
