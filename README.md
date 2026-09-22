# Demo web: Hệ thống nhận diện sự cố và cảnh báo tuyến đường

Bản cài đặt của tài liệu `demo-web-nhan-dien.md`. Một backend FastAPI + một file HTML,
chạy trên một laptop, không cần GPU.

Ba phần giao diện: **video nhận diện** → **bảng kết quả** → **bản đồ định tuyến có cảnh báo**.

Phần 1 nhận **video** (nhận diện theo từng khung, vị trí nội suy dọc hành trình xe camera) hoặc
**ảnh chụp** (nhận diện ngay, vị trí lấy theo ghim tím trên bản đồ, kéo được). Cả hai đều đổ
kết quả vào cùng bảng ở Phần 2 và cùng bản đồ ở Phần 3.

---

## 1. Cài đặt (làm một lần)

**Cần trước:**

1. **Python 3.11–3.13 (64-bit)** từ <https://www.python.org/downloads/> — khi cài **nhớ tick
   *Add python.exe to PATH***, rồi mở một cửa sổ PowerShell mới.
   *(Máy này đang dùng 3.13.15, đã chạy tốt. Python của MSYS2 có sẵn trên máy **không** dùng
   được — không cài được torch/opencv; `cai_dat.ps1` tự bỏ qua bản đó.)*
2. **Khóa OpenRouteService** (miễn phí): <https://openrouteservice.org> → Sign up →
   Dashboard → *Request a token* → loại **Standard** → sao chép chuỗi token.
   Hạn mức 2.000 lượt/ngày, thừa cho demo.

**Chạy:**

```powershell
cd D:\NgocHocLapTrinh\WebDemo
.\cai_dat.ps1
```

Script tạo `.venv`, cài thư viện (lần đầu 5–15 phút, `torch` nặng ~250 MB) và tạo file `.env`.
Mở `.env`, dán khóa vào:

```
ORS_API_KEY=5b3ce...khoa-cua-ban...
```

> Nếu PowerShell chặn script: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
>
> `cai_dat.ps1` tự dò tìm Python ở các thư mục cài đặt quen thuộc, nên vẫn chạy được kể cả khi
> gõ `python` trong terminal ra bản MSYS2.

---

## 2. Chạy demo

```powershell
.\chay.ps1        # chạy thật — cần best.pt
.\chay_thu.ps1    # CHẾ ĐỘ THỬ — chạy được ngay, chưa cần best.pt
```

Mở <http://localhost:8000>. Dừng bằng `Ctrl + C`.

Máy cần internet: để tải MapLibre, nền bản đồ OpenFreeMap và gọi OpenRouteService.

### Chế độ thử — xem web chạy trước khi có model

`chay_thu.ps1` đọc `kich_ban.thu.json` thay cho `kich_ban.json`, nên **không đụng gì tới cấu
hình thật**. Nó dùng `yolo11n.pt` (model chung của Ultralytics, tự tải ~5 MB lần đầu) và coi:

| Nhận ra | Coi như | Mức độ | Kết quả trên giao diện |
|---|---|---|---|
| Ô tô | ổ gà | 2 | Tô đỏ tuyến, cảnh báo "nên giảm tốc độ" |
| Người | ngập nước | 3 | Tô đỏ tuyến, hiện nút **Tìm tuyến né** |

Chọn một video đường phố bất kỳ (có xe và người đi bộ) là chạy được trọn luồng: bảng kết quả,
tô đỏ tuyến, hộp cảnh báo, tìm tuyến né, giọng đọc. Giao diện hiện dải vàng **CHẾ ĐỘ THỬ**
để không lỡ tay trình diễn nhầm cấu hình.

Có `best.pt` rồi thì chạy `.\chay.ps1` như bình thường, không phải sửa gì.

---

## 3. Thả model vào đâu sau khi train xong

Mỗi lần train là **một thư mục phiên bản** trong `models/`:

```
models/v1-20260925/
├── best.pt        ← model tải từ Colab
└── model.json     ← ngày train, dataset, mAP, tên lớp
```

Rồi trỏ `kich_ban.json` vào bản muốn dùng:

```json
"model": "models/v1-20260925/best.pt"
```

Giữ được bản cũ để so sánh, và giao diện hiện luôn *"Model v1 · 25/09/2026 · mAP50 0.78"*
lấy từ `model.json`. Train lần sau tệ hơn thì lùi lại chỉ mất một dòng cấu hình.

Chép thư mục mẫu `models/v1-YYYYMMDD-mau/` và file `models/model.mau.json` để bắt đầu.
Hướng dẫn đầy đủ (tải file từ Colab, viết `model.json`, kiểm tra tên lớp có khớp không)
nằm ở [`models/README.md`](models/README.md).

> Cách đơn giản hơn nếu chỉ train một lần: để `best.pt` ngay thư mục gốc và giữ
> `"model": "best.pt"`. Máy chủ tìm cả hai chỗ.

Đổi model xong nhớ **khởi động lại máy chủ** — model chỉ nạp lúc khởi động.

**Chưa có `best.pt` vẫn chạy được:** bản đồ, định tuyến, cảnh báo hoạt động bình thường;
phần nhận diện sẽ báo thiếu model. Muốn thử cả luồng nhận diện thì đổi
`kich_ban.json → "model": "yolo11n.pt"` (xem `models/README.md`).

---

## 4. Chỉnh kịch bản demo

Mọi tham số nằm trong `kich_ban.json`, sửa xong khởi động lại máy chủ.
**Mọi tọa độ là `[kinh độ, vĩ độ]`** — Google Maps cho `vĩ độ, kinh độ`, phải **đảo lại**.

| Khóa | Ý nghĩa | Mặc định |
|---|---|---|
| `model` | Đường dẫn model — `best.pt` hoặc `models/v1-20260925/best.pt` | `best.pt` |
| `nguong_tin_cay` | Bỏ phát hiện tin cậy thấp hơn | `0.5` |
| `buoc_khung` | Cứ bao nhiêu khung chạy YOLO một lần | `5` |
| `so_khung_xac_nhan` | Số khung xử lý liên tiếp mới xác nhận sự cố | `2` |
| `ban_kinh_gop_m` | Sự cố cùng loại trong bán kính này coi là một | `25` |
| `hanh_lang_m` | Sự cố cách tuyến trong khoảng này là **trên tuyến** | `30` |
| `ban_kinh_ne_m` | Bán kính vùng né quanh sự cố | `40` |
| `muc_do_doi_tuyen` | Mức độ tối thiểu để hiện nút tìm tuyến né | `3` |
| `rong_anh_gui` | Chiều rộng ảnh gửi về trình duyệt (px) | `720` |
| `phat_theo_thoi_gian_thuc` | Không xử lý nhanh hơn tốc độ video thật | `true` |
| `cho_phep_tuyen_gia` | Chưa có khóa ORS thì vẽ tuyến đường thẳng để thử giao diện | `true` |
| `lop` | Lớp dùng: khóa phải **trùng tên lớp của model** | `pothole`, `flood` |
| `xe_camera.tu` / `.den` | Hành trình xe có camera hành trình | Chợ Cần Thơ → ĐH Cần Thơ khu II |
| `diem_di` / `diem_den` | Vị trí ban đầu của ghim A, B | = hành trình xe camera |

**Để tuyến chuyển đỏ khi demo:** giữ `diem_di`/`diem_den` **bằng đúng**
`xe_camera.tu`/`xe_camera.den`. Sự cố lấy vị trí từ hành trình xe camera, nên hai tuyến
phải trùng nhau thì sự cố mới rơi vào hành lang 30 m.

**Chọn video:** dài 1–2 phút, có **cả ổ gà lẫn vùng ngập** (thiếu vùng ngập thì không có
nút tìm tuyến né), vùng ngập nên ở khoảng giữa video.

**Tuyến đang dùng:** Chợ Cần Thơ `[105.7893, 10.0349]` → ĐH Cần Thơ khu II `[105.7690, 10.0298]`,
3,38 km. Đã thử thật với ORS: chặn một điểm giữa tuyến thì tìm được tuyến né dài thêm 641 m,
vòng ra xa tới 944 m — đủ rõ trên màn hình khi trình diễn.

Đổi tuyến khác thì nhớ **thử lại tuyến né** trước khi demo: không phải cặp tọa độ nào cũng có
đường vòng, và điểm không nằm trên đường thật sẽ làm ORS báo lỗi *"Could not find routable
point"*. Lấy tọa độ bằng cách nhấp chuột phải trên Google Maps → dòng đầu là `vĩ độ, kinh độ`
→ **đảo lại** thành `[kinh độ, vĩ độ]`.

---

## 5. Cấu trúc thư mục

```
WebDemo/
├── main.py              # Backend: REST + WebSocket + gọi OpenRouteService
├── kich_ban.json        # Toàn bộ tham số demo
├── kich_ban.thu.json    # Cấu hình chế độ thử (chưa cần best.pt)
├── requirements.txt
├── .env                 # Khóa ORS (KHÔNG commit — đã .gitignore)
├── cai_dat.ps1          # Tạo venv + cài thư viện
├── chay.ps1             # Khởi động máy chủ
├── chay_thu.ps1         # Khởi động ở chế độ thử
├── models/              # Các bản model đã train, mỗi lần một thư mục phiên bản
│   ├── README.md        #   hướng dẫn lấy model từ Colab + viết model.json
│   ├── model.mau.json   #   mẫu để chép
│   └── v1-20260925/     #   best.pt + model.json
├── best.pt              # (tùy chọn) model để thẳng ở gốc, cách đơn giản hơn
├── static/index.html    # Toàn bộ giao diện 3 phần
└── uploads/             # Video tải lên, tự tạo khi chạy
```

---

## 6. Hợp đồng API

| Phương thức | Đường dẫn | Nhận |
|---|---|---|
| `GET` | `/api/kich-ban` | Cấu hình cho giao diện + `co_model`, `co_khoa_ors` |
| `POST` | `/api/video` | `{ video_id, ten, so_khung, fps, thoi_luong }` |
| `POST` | `/api/anh` | `{ ten, anh, phat_hien: [{ loai, tin_cay, anh_cat }] }` |
| `POST` | `/api/tuyen-duong` | `{ toa_do, quang_duong_m, thoi_gian_s, la_tuyen_gia }` |
| `WS` | `/ws/nhan-dien/{video_id}` | Tin `bat_dau` · `khung` · `su_co` · `ket_thuc` · `loi` |

Thử tay các API tại <http://localhost:8000/docs>.
Chi tiết từng trường: mục 8 của `demo-web-nhan-dien.md`.

---

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `cai_dat.ps1` báo không tìm thấy Python | Cài Python 3.11–3.13 từ python.org, tick *Add to PATH*, mở PowerShell **mới** |
| Dải vàng "chưa có ORS_API_KEY" | Dán khóa vào `.env` rồi khởi động lại máy chủ |
| Dải vàng "chưa nạp được model" | Thả `best.pt` vào thư mục gốc, khởi động lại máy chủ |
| Bảng sự cố trống dù "Đang thấy" có hiện | Tên lớp lệch — xem `models/README.md` |
| Bảng có sự cố nhưng tuyến không bao giờ đỏ | `diem_di`/`diem_den` lệch hành trình xe camera — xem mục 4 |
| Sự cố hiện ngoài biển, sai châu lục | Nhập nhầm `[vĩ độ, kinh độ]` — đảo lại |
| Một ổ gà tạo nhiều dòng | Tăng `ban_kinh_gop_m` lên 40–50 |
| Video chạy giật | Tăng `buoc_khung` lên 8–10, giảm `rong_anh_gui` còn 560 |
| Tìm tuyến né lỗi 502 | Vùng né che mất điểm đi/đến — chọn video có vùng ngập ở giữa, hoặc kéo ghim đi chỗ khác |
| Không đọc được `.mov` từ iPhone | Chuyển sang `.mp4` (H.264) trước khi tải lên |
| Ảnh chụp nhận diện được nhưng không hiện trên bản đồ | Kéo **ghim tím** vào gần tuyến — sự cố từ ảnh đặt đúng chỗ ghim đó |
| Không có giọng đọc tiếng Việt | Thử trên Microsoft Edge, hoặc cài giọng tiếng Việt cho Windows |
| Bản đồ trống | Kiểm tra internet; F12 xem lỗi trong tab Console |

---

## 8. Lưu ý khi trình diễn

- **Không dùng `--reload`** — mỗi lần file đổi, máy chủ nạp lại model và cắt kết nối.
- Chạy thử trọn kịch bản vài lần trước khi trình bày, và quay sẵn một video màn hình dự phòng.
- Nói rõ phần **chạy thật** (model AI, nhận diện, tìm đường, kiểm tra trên tuyến) và phần
  **mô phỏng** (nguồn video, GPS xe camera).
