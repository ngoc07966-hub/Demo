# chay.ps1 — khởi động máy chủ demo.
# Dùng:  .\chay.ps1        rồi mở http://localhost:8000
# Dừng:  Ctrl + C

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host "Chua co moi truong ao. Chay truoc:  .\cai_dat.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "May chu: http://localhost:8000   (Ctrl+C de dung)" -ForegroundColor Green
# Khong dung --reload khi trinh dien: moi lan sua file se nap lai model va cat ket noi.
& $py -m uvicorn main:app --port 8000
