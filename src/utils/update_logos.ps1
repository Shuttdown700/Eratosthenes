# Define source and destination
$Source = Join-Path $PSScriptRoot "..\..\icons\server"
$Destination = Join-Path $env:AppData "Emby-Server\system\dashboard-ui\modules\themes"

# Files to copy
$Files = @("logodark.png", "logowhite.png")

# Ensure destination exists
if (-not (Test-Path $Destination)) {
    Write-Host "Destination path not found: $Destination" -ForegroundColor Red
    exit 1
}

# Copy and overwrite
foreach ($File in $Files) {
    $SrcFile = Join-Path $Source $File
    $DstFile = Join-Path $Destination $File
    if (Test-Path $SrcFile) {
        Copy-Item -Path $SrcFile -Destination $DstFile -Force
        Write-Host "Copied $File to $Destination"
    } else {
        Write-Host "Missing source file: $SrcFile" -ForegroundColor Yellow
    }
}

Write-Host "✅ Logo update complete."
