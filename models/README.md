# Chỗ để model sau khi train xong trên Colab

## Cách đặt: mỗi lần train là một thư mục phiên bản

```
models/
├── README.md                 ← file bạn đang đọc
├── model.mau.json            ← mẫu để chép, KHÔNG phải model thật
├── v1-YYYYMMDD-mau/          ← thư mục mẫu để chép
│   └── DOC_TRUOC.md
│
├── v1-20260925/              ← bản train thật đầu tiên
│   ├── best.pt               ← model tải từ Colab
│   ├── model.json            ← ngày train, dataset, mAP, tên lớp
│   └── results.csv           ← log train từ Colab (tùy chọn)
└── v2-20261010/
    ├── best.pt
    └── model.json
```

Rồi trỏ `kich_ban.json` vào bản muốn dùng:

```json
"model": "models/v2-20261010/best.pt"
```

**Vì sao không đè thẳng lên một file `best.pt` duy nhất:**

- Train lần sau **tệ hơn** lần trước là chuyện thường. Giữ bản cũ thì lùi lại chỉ mất một dòng
  cấu hình, không phải train lại.
- Ba tháng sau nhìn một file `best.pt` trần sẽ không ai nhớ nó train từ dataset nào, bao nhiêu
  epoch, kết quả ra sao. `model.json` trả lời hộ.
- Khi demo, giao diện hiện luôn *"Model v2 · 10/10/2026 · mAP50 0.81"* — người xem biết đang
  chạy bản nào.

> Cách cũ vẫn chạy: để `best.pt` ngay thư mục gốc và giữ `"model": "best.pt"`. Máy chủ tìm cả
> hai chỗ. Dùng cách này nếu bạn chỉ train đúng một lần.

---

## Các bước sau mỗi lần train

**1. Tải `best.pt` từ Colab.** Ultralytics để file ở `runs/detect/train/weights/best.pt`
(lần train thứ hai là `train2`, thứ ba là `train3`…):

```python
from google.colab import files
files.download('runs/detect/train/weights/best.pt')
files.download('runs/detect/train/results.csv')      # tùy chọn, để xem lại đường cong train
```

Không thấy file thì kiểm tra đường dẫn thật: `!ls -R runs/detect/*/weights/`

> Lấy `best.pt` (điểm tốt nhất), **không** phải `last.pt` (lần lặp cuối).

Cách khác — lưu vào Drive rồi tải về sau:

```python
from google.colab import drive
drive.mount('/content/drive')
!cp runs/detect/train/weights/best.pt /content/drive/MyDrive/best.pt
```

**2. Tạo thư mục phiên bản.** Chép `v1-YYYYMMDD-mau/`, đổi tên thành `v<số>-<ngày>`
(ví dụ `v1-20260925`), xóa file `DOC_TRUOC.md`, thả `best.pt` vào.

**3. Viết `model.json`.** Chép `model.mau.json` vào thư mục phiên bản, đổi tên thành
`model.json`, sửa lại cho đúng:

| Khóa | Ý nghĩa | Bắt buộc |
|---|---|---|
| `phien_ban` | `v1`, `v2`… — hiện trên giao diện | Nên có |
| `ngay_train` | `YYYY-MM-DD` — giao diện tự đổi sang `DD/MM/YYYY` | Nên có |
| `nen` | Model gốc đem đi train tiếp (`yolo11n.pt`…) | Không |
| `dataset` | Tên + phiên bản Roboflow + số ảnh | Nên có |
| `epochs`, `imgsz` | Tham số train | Không |
| `lop` | Danh sách tên lớp, phải khớp `kich_ban.json` | Nên có |
| `mAP50`, `mAP50_95` | Kết quả đánh giá, lấy ở bảng cuối lần train | Nên có |
| `ghi_chu` | Lần này khác lần trước chỗ nào | Không |

Thiếu `model.json` thì model vẫn chạy bình thường, chỉ là giao diện không hiện thông tin bản train.

**4. Trỏ `kich_ban.json` vào bản mới**, rồi **khởi động lại máy chủ** (Ctrl+C rồi `.\chay.ps1`).
Model chỉ nạp một lần lúc khởi động, không nạp lại khi đang chạy.

---

## Kiểm tra tên lớp có khớp cấu hình không

Đây là lỗi hay gặp nhất: nhận diện chạy, dòng "Đang thấy" có hiện, nhưng bảng sự cố mãi trống —
vì tên lớp của model khác tên khóa trong `kich_ban.json`.

```powershell
cd D:\NgocHocLapTrinh\WebDemo
.\.venv\Scripts\python.exe -c "from ultralytics import YOLO; print(YOLO('models/v1-20260925/best.pt').names)"
```

Kết quả mong đợi:

```
{0: 'pothole', 1: 'flood'}
```

Tên in ra phải **trùng từng ký tự** với khóa trong mục `lop` của `kich_ban.json`:

```json
"lop": {
  "pothole": { "ten": "Ổ gà",      "muc_do": 2, "mau": "#F59E0B" },
  "flood":   { "ten": "Ngập nước", "muc_do": 3, "mau": "#06B6D4" }
}
```

Model đặt tên khác (ví dụ `Pothole` viết hoa, hay `water`) thì sửa **khóa** trong
`kich_ban.json` cho khớp — đừng sửa model. Phần `ten` là chữ hiển thị trên giao diện, đặt
tiếng Việt thoải mái.

Máy chủ cũng tự kiểm tra việc này lúc khởi động và in cảnh báo ra terminal nếu lệch.

---

## Về Git

`.gitignore` chặn mọi file `*.pt` **trừ `best.pt`** (cả ở thư mục gốc lẫn trong
`models/<phiên bản>/`). Model YOLO11n tự train chỉ ~5 MB, dưới xa giới hạn 100 MB/file của
GitHub, nên commit thẳng lên để clone về là chạy được ngay. `model.json` cũng được commit,
nên lịch sử các lần train nằm đủ trong repo.

`yolo11n.pt` (model mẫu của Ultralytics) vẫn bị bỏ qua — nó tự tải khi chạy chế độ thử.

Nếu sau này model vượt ~50 MB (GitHub bắt đầu cảnh báo), chuyển sang đính kèm vào
GitHub Releases hoặc Google Drive và ghi link trong `ghi_chu` của `model.json`.

---

## Chưa có model thì thử giao diện thế nào

Chạy `.\chay_thu.ps1` ở thư mục gốc. Script này đọc `kich_ban.thu.json` thay cho
`kich_ban.json`, nên **không phải sửa gì và không đụng tới cấu hình thật**.

Chế độ thử dùng `yolo11n.pt` (tự tải ~5 MB lần đầu), coi "Ô tô" như sự cố mức 2 và "Người"
như sự cố mức 3. Chọn một video đường phố bất kỳ là chạy được trọn luồng: bảng kết quả, tô đỏ
tuyến, nút tìm tuyến né, giọng đọc — y như thật, chỉ khác tên lớp. Giao diện hiện dải vàng
**CHẾ ĐỘ THỬ** để không lỡ tay trình diễn nhầm.

Có model thật rồi thì chạy `.\chay.ps1`, không phải sửa gì.
