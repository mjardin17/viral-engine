@echo off
:: Empire OS System Audit — Execution Policy Bypass Launcher
:: Double-click this file to run the full system audit
powershell.exe -ExecutionPolicy Bypass -File "%~dp0EMPIRE_AUDIT.ps1"
