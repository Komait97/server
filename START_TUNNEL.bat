@echo off
chcp 65001 >nul
title KOMAIT - Tunnel
cd /d "%~dp0"
if not exist cloudflared.exe (
    echo Downloading Cloudflare Tunnel...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'" 2>nul
    if not exist cloudflared.exe curl -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -o cloudflared.exe
)
echo.
echo ============================================
echo COPY THE URL BELOW (https://xxx.trycloudflare.com)
echo ============================================
echo.
cloudflared.exe tunnel --no-autoupdate --url http://localhost:5001
pause
