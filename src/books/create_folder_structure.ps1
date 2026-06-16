$files = Get-ChildItem -File
Write-Host "Found $($files.Count) files to process." -ForegroundColor Cyan

foreach ($file in $files) {
    # Use BaseName to get the filename WITHOUT the extension (.cbr/.cbz)
    $FolderName = $file.BaseName
    
    Write-Host "Organizing: $($file.Name) into folder [$FolderName]" -ForegroundColor Yellow
    
    # Create the clean folder
    $null = New-Item -ItemType Directory -Name $FolderName -Force
    
    # Combine paths using the clean folder name
    $TargetDestination = Join-Path -Path $file.DirectoryName -ChildPath $FolderName
    
    # Move the file
    Move-Item -Path $file.FullName -Destination $TargetDestination
}