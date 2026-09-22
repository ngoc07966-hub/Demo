# cai_dat.ps1 — chạy MỘT LẦN để tạo môi trường ảo và cài thư viện.
# Dùng:  .\cai_dat.ps1
# Nếu PowerShell chặn script:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# ── Tìm Python thật ──
# Bỏ qua Python cua MSYS2 (C:\msys64\...): khong co wheel cho torch/opencv tren ban nay.
# Khong chi dua vao PATH — may nay PATH van uu tien MSYS2 — nen do them cac cho cai dat quen thuoc.
function Tim-Python {
    $ungVien = @()

    # 1. Cac thu muc cai dat thong thuong cua python.org (moi nhat truoc)
    foreach ($goc in @("$env:LOCALAPPDATA\Programs\Python", 'C:\Program Files', 'C:')) {
        if (-not (Test-Path $goc)) { continue }
        $ungVien += Get-ChildItem $goc -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending |
                    ForEach-Object { Join-Path $_.FullName 'python.exe' }
    }

    # 2. Trinh khoi chay py.exe (neu co) va python tren PATH
    $ungVien += "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe"
    $ungVien += 'C:\Windows\py.exe'
    $ungVien += (Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object Source)

    foreach ($ung in $ungVien) {
        if (-not $ung -or -not (Test-Path $ung)) { continue }
        try { $that = & $ung -c "import sys; print(sys.executable)" 2>$null } catch { continue }
        if (-not $that -or $that -like '*msys64*') { continue }   # Python MSYS2 — khong dung duoc
        # Phai co pip thi moi cai duoc thu vien
        & $ung -m pip --version *> $null
        if (-not $?) { continue }
        return $that
    }
    return $null
}

$py = Tim-Python
if (-not $py) {
    Write-Host ""
    Write-Host "Khong tim thay Python dung duoc." -ForegroundColor Red
    Write-Host "Hay cai Python 3.11 - 3.13 (64-bit) tu https://www.python.org/downloads/"
    Write-Host "Khi cai NHO TICK: 'Add python.exe to PATH'."
    Write-Host "Cai xong thi MO POWERSHELL MOI roi chay lai script nay."
    exit 1
}
Write-Host "Dung Python: $py" -ForegroundColor Cyan
& $py --version

# ── Tạo môi trường ảo ──
if (-not (Test-Path '.venv')) {
    Write-Host "Tao moi truong ao .venv ..." -ForegroundColor Cyan
    & $py -m venv .venv
}

$pyVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Write-Host "Cai thu vien (lan dau mat 5-15 phut, torch nang ~250MB) ..." -ForegroundColor Cyan
& $pyVenv -m pip install --upgrade pip
& $pyVenv -m pip install -r requirements.txt

# ── Tạo .env nếu chưa có ──
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host ""
    Write-Host "Da tao file .env — hay mo ra dan khoa OpenRouteService vao." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "XONG. Chay demo bang:  .\chay.ps1" -ForegroundColor Green
