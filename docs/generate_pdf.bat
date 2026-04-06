@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Yana OS — Documentation PDF Generator (Windows)
REM  Usage: Double-click or run from Command Prompt
REM  Output: docs\YANA_OS_USER_MANUAL.pdf
REM ═══════════════════════════════════════════════════════════════

echo.
echo  ⚡ Yana OS — PDF Generator
echo  ─────────────────────────────────────────────────────

SET SCRIPT_DIR=%~dp0
SET HTML_FILE=%SCRIPT_DIR%YANA_OS_USER_MANUAL.html
SET PDF_FILE=%SCRIPT_DIR%YANA_OS_USER_MANUAL.pdf

REM ─── Try Chrome (most reliable HTML-to-PDF) ───────────────────
SET CHROME_PATHS[0]=%PROGRAMFILES%\Google\Chrome\Application\chrome.exe
SET CHROME_PATHS[1]=%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe
SET CHROME_PATHS[2]=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe

FOR %%P IN (
  "%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"
  "%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"
  "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) DO (
  IF EXIST %%P (
    echo  Using Google Chrome to generate PDF...
    %%P --headless=new --disable-gpu --no-sandbox --print-to-pdf="%PDF_FILE%" --no-pdf-header-footer "%HTML_FILE%"
    IF EXIST "%PDF_FILE%" (
      echo  ✓ PDF saved to: %PDF_FILE%
      goto :DONE
    )
  )
)

REM ─── Try Edge (built into Windows 11) ─────────────────────────
FOR %%P IN (
  "%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"
  "%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"
) DO (
  IF EXIST %%P (
    echo  Using Microsoft Edge to generate PDF...
    %%P --headless=new --disable-gpu --no-sandbox --print-to-pdf="%PDF_FILE%" --no-pdf-header-footer "%HTML_FILE%"
    IF EXIST "%PDF_FILE%" (
      echo  ✓ PDF saved to: %PDF_FILE%
      goto :DONE
    )
  )
)

REM ─── Manual instructions fallback ─────────────────────────────
echo.
echo  Chrome/Edge not found in standard locations.
echo.
echo  MANUAL PDF GENERATION:
echo  1. Open in Chrome/Edge: %HTML_FILE%
echo  2. Press Ctrl+P
echo  3. Destination: Save as PDF
echo  4. Paper: A4,  Margins: Default,  Background graphics: ON
echo  5. Click Save
echo.

:DONE
echo.
pause
