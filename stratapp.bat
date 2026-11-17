@echo off
chcp 65001
cd /d D:\AutoMaint-Agent
call .venv\Scripts\activate
streamlit run app.py