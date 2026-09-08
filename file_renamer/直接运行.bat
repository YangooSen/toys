@echo off
chcp 65001 >nul
pip install pypdf >nul 2>&1
python file_renamer.py
if errorlevel 1 pause
