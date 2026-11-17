@echo off
chcp 65001
cd /d D:\AutoMaint-Agent
call .venv\Scripts\python.exe agent_core.py >> agent_log.txt 2>&1