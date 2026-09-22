# chay_thu.ps1 — chạy demo ở CHẾ ĐỘ THỬ, khi chưa có best.pt.
#
# Dùng kich_ban.thu.json thay cho kich_ban.json, nên KHÔNG đụng gì tới cấu hình thật.
# Model yolo11n.pt chính thức của Ultralytics tự tải về lần đầu (~5 MB).
# Coi "Ô tô" như sự cố mức 2 và "Người" như sự cố mức 3 — đủ để thử trọn luồng:
# bảng kết quả, tô đỏ tuyến, hộp cảnh báo, nút Tìm tuyến né, giọng đọc.
#
# Dùng:  .\chay_thu.ps1     rồi mở http://localhost:8000 và chọn một video đường phố bất kỳ
# Dừng:  Ctrl + C

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host "Chua co moi truong ao. Chay truoc:  .\cai_dat.ps1" -ForegroundColor Red
    exit 1
}

$env:KICH_BAN = 'kich_ban.thu.json'
Write-Host "CHE DO THU — dung kich_ban.thu.json, khong dung best.pt" -ForegroundColor Yellow
Write-Host "May chu: http://localhost:8000   (Ctrl+C de dung)" -ForegroundColor Green
& $py -m uvicorn main:app --port 8000
