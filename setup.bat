@echo off
chcp 65001 >nul
title RAG2 首次安装

echo.
echo ╔════════════════════════════════════════════╗
echo ║      RAG2 智能笔记助手 — 首次安装        ║
echo ╚════════════════════════════════════════════╝
echo.

:: ========== 检查 Python ==========
echo [1/5] 检查 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Python，请先安装 Python 3.12+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo    Python %%i ✓

:: ========== 检查 Node.js ==========
echo [2/5] 检查 Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Node.js，请先安装 Node.js 18+
    echo   下载地址: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version 2^>^&1') do echo    Node.js %%i ✓

:: ========== 检查/安装 Ollama ==========
echo [3/5] 检查 Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   [提示] 未找到 Ollama，将跳过本地模型检查
    echo   如需本地嵌入模型，请访问 https://ollama.com 下载安装
    echo   然后运行: ollama pull qwen3-embedding:0.6b
) else (
    echo   Ollama 已安装 ✓
    echo   正在拉取嵌入模型 qwen3-embedding:0.6b...
    ollama pull qwen3-embedding:0.6b
)

:: ========== 安装 Python 依赖 ==========
echo [4/5] 安装 Python 依赖...
cd /d "%~dp0backend"
if not exist ".venv" (
    echo   正在创建虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -e . --quiet 2>nul
if %errorlevel% neq 0 (
    uv sync --quiet 2>nul
)
echo   Python 依赖安装完成 ✓

:: ========== 安装前端依赖 ==========
echo [5/5] 安装前端依赖...
cd /d "%~dp0front"
if not exist "node_modules" (
    call npm install --silent
)
echo   前端依赖安装完成 ✓

:: ========== 检查配置文件 ==========
cd /d "%~dp0backend"
if not exist ".env" (
    echo.
    echo ╔════════════════════════════════════════════╗
    echo ║  未检测到 .env 配置文件                   ║
    echo ║  请编辑 backend\.env 填入你的 API Key      ║
    echo ╚════════════════════════════════════════════╝
    copy .env.example .env >nul
    echo   已从 .env.example 创建 .env 模板
    echo   请用记事本打开 backend\.env 填入 DEEPSEEK_API_KEY
    notepad .env
)

echo.
echo ╔════════════════════════════════════════════╗
echo ║         安装完成！                        ║
echo ║  双击 start.bat 启动 RAG2                 ║
echo ╚════════════════════════════════════════════╝
echo.
pause
