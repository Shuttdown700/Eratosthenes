@echo off
TITLE Extract English Audio + Subtitles from MKVs

setlocal enabledelayedexpansion
set FFMPATH="C:\Users\brend\Documents\Coding Projects\alexandria_media_manager\src\bin\ffmpeg.exe"
set FFPROBE="C:\Users\brend\Documents\Coding Projects\alexandria_media_manager\src\bin\ffprobe.exe"
set OUTDIR=filtered

set "FILES_FOUND=0"
set "FILES_PROCESSED=0"

REM Create output directory if it doesn't exist
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

REM === Loop through MKV files ===
for %%i in (*.mkv) do (
    set "FILES_FOUND=1"
    set "FILENAME=%%~ni"
    set "OUTFILE=%OUTDIR%\!FILENAME!.mkv"

    if exist "!OUTFILE!" (
        echo Skipping: "!OUTFILE!" already exists.
    ) else (
        echo Processing: %%i
        %FFMPATH% -i "%%i" ^
            -map 0 -map -0:a -map -0:s ^
            -map 0:a:m:language:eng -map 0:s ^
            -c copy "!OUTFILE!"
        set /a FILES_PROCESSED+=1
    )
)

REM === Check for missing audio tracks ===
if !FILES_FOUND! EQU 1 (
    echo.
    echo ================================
    echo Checking for missing audio tracks...
    echo ================================

    for %%i in (*.mkv) do (
        set "HAS_AUDIO="
        for /f %%A in ('%FFPROBE% -v error -select_streams a -show_entries stream=index -of csv=p=0 "%%i"') do (
            set "HAS_AUDIO=1"
            goto :has_audio
        )
        :no_audio
        if not defined HAS_AUDIO (
            echo WARNING: "%%i" has no audio track!
        )
        :has_audio
    )
) else (
    echo No .mkv files found in this directory.
)

echo.
echo ================================
echo Script finished.
echo !FILES_PROCESSED! file(s) were processed.
echo Press any key to exit...
pause > nul
