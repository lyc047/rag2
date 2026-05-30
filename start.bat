@echo off
chcp 65001 >nul
title RAG2 智能笔记助手

echo.
echo ╔════════════════════════════════════════════╗
echo ║       RAG2 智能笔记助手 v2.0.0            ║
echo ╚════════════════════════════════════════════╝
echo.

:: ========== 前置检查 ==========
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先运行 setup.bat
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先运行 setup.bat
    pause
    exit /b 1
)

cd /d "%~dp0backend"
if not exist ".env" (
    echo [错误] 未找到 .env 配置文件
    echo 请复制 backend\.env.example 为 backend\.env 并填入配置
    pause
    exit /b 1
)

:: ========== 检查 Ollama ==========
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo [提示] Ollama 未运行，正在启动...
        start "" "ollama" serve
        timeout /t 3 /nobreak >nul
    )
    echo Ollama 已就绪 ✓
) else (
    echo [警告] 未安装 Ollama，知识库上传功能可能不可用
)

:: ========== 启动后端 ==========
echo.
echo 正在启动后端服务 (端口 8005)...
cd /d "%~dp0backend"
start "RAG2-Backend" .venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8005

:: 等待后端就绪
echo 等待后端就绪...
:wait_backend
timeout /t 1 /nobreak >nul
curl -s http://localhost:8005/health/live >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
echo 后端已启动 ✓

:: ========== 启动前端 ==========
echo 正在启动前端服务 (端口 3001)...
cd /d "%~dp0front"
start "RAG2-Frontend" cmd /c "npm run dev"

:: 等待前端就绪
echo 等待前端就绪...
:wait_frontend
timeout /t 1 /nobreak >nul
curl -s http://localhost:3001 >nul 2>&1
if %errorlevel% neq 0 goto wait_frontend
echo 前端已启动 ✓

:: ========== 打开浏览器 ==========
echo.
echo ╔════════════════════════════════════════════╗
echo ║  启动完成！正在打开浏览器...             ║
echo ║  前端地址: http://localhost:3001          ║
echo ║  API 文档: http://localhost:8005/docs     ║
echo ║  关闭此窗口将停止所有服务                ║
echo ╚════════════════════════════════════════════╝
start http://localhost:3001

echo.
echo 按任意键停止所有服务...
pause >nul

:: ========== 清理 ==========
echo 正在停止服务...
taskkill /fi "WINDOWTITLE eq RAG2-Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq RAG2-Frontend*" /f >nul 2>&1
echo 服务已停止
