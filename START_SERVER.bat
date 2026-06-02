@echo off
chcp 65001 >nul
title KOMAIT - Server
cd /d "%~dp0"
pip install requests colorama -q 2>nul
echo Starting server...
python server_bot.py
pause
