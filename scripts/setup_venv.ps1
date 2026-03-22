# 在项目根目录创建 .venv 并安装依赖（需已安装 Python 3.10+）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $py) {
    Write-Error "未找到 py 或 python。请先安装 Python 3.10+ 并勾选「Add Python to PATH」。"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "创建虚拟环境: $Root\.venv"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } else {
        python -m venv .venv
    }
}

$req = Join-Path $Root "requirements.txt"
if (-not (Test-Path $req)) {
    Write-Error "未找到依赖文件: $req（应包含 -r backend/requirements.txt 与 Streamlit 等）"
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $req

Write-Host ""
Write-Host "完成。激活虚拟环境（PowerShell）："
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "运行后端 CLI（backend 目录）："
Write-Host "  Set-Location backend; python main.py `"示例评论`""
Write-Host "运行第三周前端（项目根目录）："
Write-Host "  streamlit run frontend\app.py"
