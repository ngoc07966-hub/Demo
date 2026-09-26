# Kế hoạch triển khai công nghệ
## Hệ thống cảnh báo sự cố giao thông và định tuyến thông minh dựa trên AI

> **Tài liệu dành cho cả người và AI đọc.**
> Các tên hàm, tên trường, tên lớp, thứ tự tọa độ và tham số trong tài liệu này là **hợp đồng đã chốt** — mọi thành viên và mọi công cụ AI hỗ trợ lập trình phải tuân thủ, không tự ý đổi.

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 1.0 |
| Ngày cập nhật | 22/09/2026 |
| Mục đích | Bản demo cho cuộc thi AI — chủ đề phát triển kinh tế – xã hội |
| Thời gian thực hiện | 10 ngày |
| Khu vực demo | Thành phố Cần Thơ |
| Ngôn ngữ giao diện | Tiếng Việt |

---

## Mục lục

0. [Ghi chú cho AI hỗ trợ lập trình](#0-ghi-chú-cho-ai-hỗ-trợ-lập-trình)
1. [Tóm tắt dự án](#1-tóm-tắt-dự-án)
2. [Phạm vi: hệ thống thật và bản demo](#2-phạm-vi-hệ-thống-thật-và-bản-demo)
3. [Kiến trúc](#3-kiến-trúc)
4. [Công nghệ sử dụng](#4-công-nghệ-sử-dụng)
5. [Hợp đồng dữ liệu](#5-hợp-đồng-dữ-liệu)
6. [Tham số nghiệp vụ](#6-tham-số-nghiệp-vụ)
7. [Luồng A — AI](#7-luồng-a--ai)
8. [Luồng B — Cloud](#8-luồng-b--cloud)
9. [Luồng C — App người nhận](#9-luồng-c--app-người-nhận)
10. [Lịch triển khai 10 ngày](#10-lịch-triển-khai-10-ngày)
11. [Thứ tự bắt đầu và phân công](#11-thứ-tự-bắt-đầu-và-phân-công)
12. [Rủi ro và phương án dự phòng](#12-rủi-ro-và-phương-án-dự-phòng)
13. [Danh sách bẫy kỹ thuật](#13-danh-sách-bẫy-kỹ-thuật)
14. [Kịch bản demo](#14-kịch-bản-demo)
15. [Hướng phát triển hệ thống thật](#15-hướng-phát-triển-hệ-thống-thật)
16. [Tài liệu tham khảo](#16-tài-liệu-tham-khảo)
17. [Thuật ngữ](#17-thuật-ngữ)

---

## 0. Ghi chú cho AI hỗ trợ lập trình

Khi dùng tài liệu này làm ngữ cảnh cho một trợ lý AI, trợ lý cần tuân thủ:

1. **Giữ đúng phạm vi demo** (mục 2). Không đề xuất thêm công nghệ ngoài bảng ở mục 4 trừ khi được yêu cầu.
2. **Tuân thủ hợp đồng dữ liệu** (mục 5) tuyệt đối: tên lớp, tên hàm, tên tham số, thứ tự tọa độ.
3. **Dùng tham số ở mục 6**, không tự đặt con số khác.
4. Nhóm phát triển **mới làm quen** với machine learning và Flutter: giải thích ngắn gọn, code có chú thích tiếng Việt, ưu tiên giải pháp đơn giản chạy được hơn giải pháp tối ưu phức tạp.
5. Tên biến, tên hàm trong code có thể dùng tiếng Việt không dấu (như trong tài liệu) để thống nhất.
6. Trong Flutter, **mọi logic phải dùng kiểu `ViTri` của dự án**, không dùng trực tiếp `Position` của geolocator (xem mục 9.4).

---

## 1. Tóm tắt dự án

**Vấn đề:** Tài xế không biết trước những đoạn đường đang ngập, có ổ gà lớn hay vật cản. Họ chỉ phát hiện khi đã ở ngay trước sự cố — quá muộn để tránh hoặc đổi tuyến.

**Giải pháp:** Các xe có **camera hành trình** dùng AI tự động phát hiện sự cố trên đường và gửi vị trí về một **kho dữ liệu chung**. Mọi người dùng app đều nhận được **cảnh báo về đúng tuyến đường mình đang đi**, và được **gợi ý tuyến né** khi đường phía trước không đi được.

**Giá trị cốt lõi:** Xe B được cảnh báo nhờ camera của xe A — từ cách xa hàng km, trước khi nhìn thấy sự cố. Người nhận cảnh báo **không cần có camera**.

**Hai vai trò trong hệ thống:**

| Vai trò | Là ai | Làm gì |
|---|---|---|
| **Nguồn dữ liệu** | Xe có camera hành trình (taxi, xe công nghệ, xe buýt) | Nhận diện sự cố bằng AI, gửi lên cloud |
| **Người nhận** | Bất kỳ ai cài app | Nhận cảnh báo theo tuyến, đổi tuyến khi cần |

---

## 2. Phạm vi: hệ thống thật và bản demo

| Thành phần | Hệ thống thật | Bản demo |
|---|---|---|
| Nguồn hình ảnh | Camera hành trình ô tô | **Video tự quay**, phát trên laptop |
| GPS của nguồn | GPS tích hợp camera hành trình | **Tuyến tọa độ mô phỏng**, nội suy theo tiến độ video |
| Dữ liệu train | Ảnh thu từ camera hành trình tại Việt Nam | **Dataset công khai từ Roboflow Universe** |
| Nơi chạy AI nhận diện | Thiết bị gắn trên xe | **Python + Ultralytics trên laptop** |
| Kho dữ liệu chung | Backend tự vận hành | **Supabase** (gói miễn phí) |
| App người nhận | Android + iOS | **Flutter, chạy trên Android** |
| Vị trí người nhận | GPS thật | GPS thật **hoặc chế độ mô phỏng** |
| Tìm đường | Máy chủ định tuyến tự vận hành | **OpenRouteService** (dịch vụ công cộng) |

**Trong phạm vi demo:**
- Model AI nhận diện ổ gà và vùng ngập
- Script mô phỏng xe có camera hành trình gửi sự cố lên cloud
- Kho sự cố chung, gộp sự cố trùng, tự hết hạn
- App: bản đồ, lộ trình, nhận sự cố thời gian thực, lọc theo hành lang tuyến, cảnh báo giọng nói theo mức, đổi tuyến né

**Ngoài phạm vi demo** (chỉ trình bày trên slide):
- Thu thập dữ liệu thật từ camera hành trình, vòng lặp train lại định kỳ
- Làm mờ khuôn mặt và biển số trên ảnh thu thập
- Chống gian lận bằng đếm số thiết bị khác nhau
- Làm thô tọa độ bằng lưới H3, cache Redis, backend tự vận hành
- Web dashboard cho cơ quan quản lý
- iOS, chạy nền, dẫn đường từng ngã rẽ

---

## 3. Kiến trúc

### 3.1 Sơ đồ bản demo

```
LAPTOP — mô phỏng xe có camera hành trình        ĐIỆN THOẠI — app người nhận
┌──────────────────────────────────┐            ┌───────────────────────────────┐
│ Video đường phố                  │            │ Bản đồ MapLibre + OpenFreeMap │
│  → YOLO (Python, Ultralytics)    │            │ Vị trí (GPS thật / mô phỏng)  │
│  → gắn tọa độ theo tuyến mô phỏng│            │ Lộ trình (OpenRouteService)   │
│  → chống gửi trùng               │            │ SQLite: bản sao, hàng đợi,    │
│  → gọi bao_cao_su_co             │            │         nhật ký cảnh báo      │
│ Cửa sổ hiện video + khung AI     │            │ Lọc hành lang → cảnh báo TTS  │
└────────────────┬─────────────────┘            │ → đổi tuyến                   │
                 │ HTTPS + JSON                 └──────────────▲────────────────┘
                 ▼                                             │ WebSocket (Realtime)
        ┌─────────────────────────────────────┐               │ + HTTPS (prefetch)
        │ SUPABASE                            │───────────────┘
        │ PostgreSQL + PostGIS                │
        │ Bảng su_co · hàm bao_cao_su_co      │
        │           · hàm su_co_gan_day       │
        └─────────────────────────────────────┘

GIAI ĐOẠN PHÁT TRIỂN (một lần):
  Roboflow Universe ──ảnh có nhãn──► Google Colab (GPU) ──train──► best.pt ──chép──► laptop
```

### 3.2 Năm cơ chế giao tiếp

| Cơ chế | Giữa | Cần mạng |
|---|---|---|
| Chuyển file | Colab → laptop (`best.pt`) | Không (làm một lần) |
| Gọi hàm, callback, stream | Các phần code trong app | Không |
| Platform channel | Dart ↔ phần cứng điện thoại (GPS, loa) | Không |
| SQL cục bộ | App ↔ SQLite | Không |
| HTTPS + JSON, WebSocket | Laptop/App ↔ Supabase, App ↔ OpenRouteService, App ↔ máy chủ bản đồ | **Có** |

### 3.3 Nguyên tắc thiết kế

| Nguyên tắc | Ý nghĩa |
|---|---|
| **Xử lý tại nguồn** | Nguồn chỉ gửi bản ghi sự cố (~150 byte), không gửi video |
| **Tải trước theo vùng (prefetch)** | App tải sự cố quanh khu vực vào SQLite, tự đối chiếu cục bộ; không để máy chủ theo dõi từng xe |
| **Lọc theo hành lang tuyến** | Chỉ cảnh báo sự cố nằm trên đúng tuyến đang đi, phía trước xe |
| **Phân mức cảnh báo** | Chỉ sự cố nguy hiểm mới phát âm thanh |
| **Suy giảm từng phần** | Mất mạng thì mất tính năng chia sẻ, nhưng cảnh báo từ dữ liệu đã tải vẫn chạy |

---

## 4. Công nghệ sử dụng

| Tầng | Công nghệ | Vai trò trong dự án | Luồng |
|---|---|---|---|
| Dữ liệu train | **Roboflow Universe** | Dataset ổ gà, ngập đã gán nhãn; gộp, đổi tên lớp, export định dạng YOLO | A |
| Môi trường train | **Google Colab** (GPU T4) | Train và đánh giá model; lưu kết quả vào Google Drive | A |
| Model AI | **Ultralytics YOLO** — `yolo11n.pt` hoặc `yolo26n.pt` (bản nano) | Phát hiện `pothole`, `flood` | A |
| Nhận diện trên video | **Python 3.10+**, `ultralytics`, `opencv-python` | Chạy model lên video, hiện cửa sổ kết quả | A |
| Kết nối cloud (Python) | `supabase` (supabase-py) | Gọi `bao_cao_su_co` | A |
| Cơ sở dữ liệu | **Supabase**: PostgreSQL + **PostGIS** | Kho sự cố chung, truy vấn theo vị trí | B |
| API tự sinh | Supabase PostgREST | Biến hàm SQL thành API `/rest/v1/rpc/...` | B |
| Đẩy thời gian thực | Supabase **Realtime** (WebSocket) | Đẩy sự cố mới xuống app | B |
| Bảo mật | **Row Level Security** | Chỉ cho đọc bảng, chỉ cho ghi qua hàm | B |
| Framework app | **Flutter + Dart** (Android) | App người nhận | C |
| Bản đồ | `maplibre_gl` + **OpenFreeMap** (style `liberty`) | Nền bản đồ, vẽ sự cố và lộ trình | C |
| Định vị | `geolocator` | Vị trí, hướng, tốc độ, tính khoảng cách | C |
| Lưu cục bộ | `sqflite` (SQLite) | Bản sao sự cố vùng, hàng đợi, nhật ký cảnh báo | C |
| Giọng nói | `flutter_tts` (giọng `vi-VN`) | Đọc cảnh báo | C |
| Tìm đường | **OpenRouteService** qua `http` | Lộ trình, tuyến né bằng `avoid_polygons` | C |
| Kết nối cloud (Dart) | `supabase_flutter` | Prefetch, Realtime | C |
| Dữ liệu bản đồ nền | **OpenStreetMap** | Nền của OpenFreeMap và OpenRouteService | — |

**Không dùng trong demo:** plugin `ultralytics_yolo`, export `.tflite`, camera trong app, FastAPI, Redis, H3, GraphHopper, Docker, Kafka, Kubernetes.

---

## 5. Hợp đồng dữ liệu

> **Bắt buộc tuân thủ.** Mọi luồng đều dựa vào các quy ước dưới đây.

### 5.1 Lớp sự cố và mức độ

| Tên lớp (chính xác, chữ thường) | Ý nghĩa | Mức độ mặc định | Thời hạn |
|---|---|---|---|
| `pothole` | Ổ gà, mặt đường hư hỏng | `2` | 60 ngày |
| `flood` | Vùng ngập nước | `3` | 4 giờ |

Các lớp khác model có thể trả về (ví dụ `manhole`) được **bỏ qua**, không gửi lên cloud.

**Thang mức độ:**
- `1` — nhẹ: chỉ hiện trên bản đồ
- `2` — vừa: cảnh báo
- `3` — nghiêm trọng, không đi được: cảnh báo và đổi tuyến

### 5.2 Thứ tự tọa độ

| Nơi dùng | Thứ tự |
|---|---|
| GeoJSON, OpenRouteService, MapLibre source | **`[kinh độ, vĩ độ]`** |
| Dart `LatLng(...)`, Python tuple trong dự án, tham số hàm Supabase | **`(vĩ độ, kinh độ)`** — tham số hàm có tên `p_lat`, `p_lon` riêng |
| PostGIS `ST_MakePoint(...)` | **`(kinh độ, vĩ độ)`** |

Tọa độ dùng hệ **WGS84 (SRID 4326)**, độ thập phân, tối thiểu 5 chữ số sau dấu phẩy.

### 5.3 API Supabase

**Ghi — `bao_cao_su_co`**

| Tham số | Kiểu | Ví dụ |
|---|---|---|
| `p_loai` | text | `"flood"` |
| `p_muc_do` | int | `3` |
| `p_lat` | float8 | `10.0341` |
| `p_lon` | float8 | `105.7880` |

Hành vi: nếu đã có sự cố **cùng loại, còn hạn, trong vòng 25 m** → tăng `so_bao_cao`, nâng `muc_do` nếu cao hơn, gia hạn `het_han`. Nếu chưa có → tạo mới. Không trả dữ liệu.

**Đọc — `su_co_gan_day`**

| Tham số | Kiểu | Mặc định |
|---|---|---|
| `p_lat` | float8 | — |
| `p_lon` | float8 | — |
| `p_ban_kinh` | int (mét) | `10000` |

Trả về danh sách: `id`, `loai`, `muc_do`, `lat`, `lon`, `so_bao_cao` — chỉ những sự cố còn hạn.

**Realtime:** app đăng ký thay đổi (`INSERT`, `UPDATE`) của bảng `public.su_co`.

### 5.4 Bản ghi sự cố trong app

```json
{
  "id": 4172,
  "loai": "flood",
  "muc_do": 3,
  "lat": 10.0341,
  "lon": 105.7880,
  "so_bao_cao": 1,
  "tren_tuyen": true
}
```

Trường `tren_tuyen` do app tự tính sau khi lọc hành lang, không lưu trên cloud.

### 5.5 Kích thước ảnh

Train và nhận diện đều dùng `imgsz=640`.

---

## 6. Tham số nghiệp vụ

| Tham số | Giá trị | Dùng ở |
|---|---|---|
| Ngưỡng độ tin cậy nhận diện | `0.55` | Luồng A |
| Tần suất xử lý video | 1 trên 5 khung hình (`vid_stride=5`) | Luồng A |
| Bán kính gộp sự cố trùng | `25 m` | A (chống gửi trùng), B (gộp) |
| Thời hạn `flood` / `pothole` | `4 giờ` / `60 ngày` | B |
| Bán kính prefetch | `10 000 m` | C |
| Chu kỳ prefetch lại | `5 phút` | C |
| Độ rộng hành lang tuyến | `±30 m` | C |
| Khoảng cách phát cảnh báo | `tốc độ (m/s) × 9 + 30 m` | C |
| Nón hướng phía trước (chế độ tự do) | `±35°` | C |
| Tốc độ tối thiểu để tin hướng GPS | `1.5 m/s` | C |
| Sai số GPS tối đa chấp nhận | `30 m` | C |
| Điều kiện chệch tuyến | cách tuyến `> 40 m` liên tục `6 giây` | C |
| Bán kính vùng né quanh sự cố | `40 m` (đa giác 12 cạnh) | C |
| Khoảng cách tối thiểu giữa hai lần đổi tuyến | `2 phút` | C |
| Không đổi tuyến khi đã cách sự cố dưới | `150 m` | C |
| Không nhắc lại cùng sự cố trong | `12 giờ` | C |
| Ngân sách cảnh báo âm thanh | tối đa 1 lần / `45 giây` | C |
| Tốc độ xe ở chế độ mô phỏng | `8.3 m/s` (≈ 30 km/h) | C |

---

## 7. Luồng A — AI

**Mục tiêu:** Có model nhận diện `pothole`, `flood` và script mô phỏng xe có camera hành trình gửi sự cố lên Supabase.

**Đầu vào:** Dataset Roboflow, video đường tự quay.
**Đầu ra:** File `best.pt`; script `xe_camera_hanh_trinh.py`.

### 7.1 Chuẩn bị dữ liệu trên Roboflow

1. Fork dataset ổ gà và dataset ngập về workspace.
2. Gộp vào một dự án. **Đổi tên lớp** cho khớp hợp đồng: `pothole`, `flood` (chữ thường).
3. Giữ lớp `manhole` nếu có — giúp model phân biệt nắp cống với ổ gà (app sẽ bỏ qua lớp này).
4. Generate version: resize 640, augmentation (lật ngang, độ sáng, làm mờ).
5. Export định dạng YOLO, copy đoạn code tải về.

**Quyết định:** Dùng model **detection** (khung chữ nhật) cho cả hai lớp, vì phần lớn dataset ổ gà chỉ có nhãn dạng hộp. Segmentation là tùy chọn nếu có dataset ngập với nhãn đa giác.

### 7.2 Train trên Colab

```python
# Ô 1 — Kiểm tra GPU (Runtime → Change runtime type → T4 GPU)
!nvidia-smi

# Ô 2 — Nối Google Drive để không mất kết quả khi phiên bị ngắt
from google.colab import drive
drive.mount('/content/drive')

# Ô 3 — Cài thư viện
!pip install -q ultralytics roboflow

# Ô 4 — Dán đoạn code tải dataset từ Roboflow vào đây
!pip install roboflow

from roboflow import Roboflow
rf = Roboflow(api_key="ztqRHZGlNe6XI5sDzgVU")
project = rf.workspace("ha-hien-vi-van").project("pothole-detection-bqu6s-9dhlm")
version = project.version(1)
dataset = version.download("yolov11")
                

# Ô 5 — Train
from ultralytics import YOLO
model = YOLO("yolo11n.pt")                      # file .pt — KHÔNG dùng .yaml
model.train(
    data="<duong-dan>/data.yaml",
    epochs=80, imgsz=640, patience=20,
    project="/content/drive/MyDrive/yolo", name="duong",
)

# Ô 6 — Đánh giá
best = YOLO("/content/drive/MyDrive/yolo/duong/weights/best.pt")
metrics = best.val()                            # Precision, Recall, mAP50
best.predict("<anh-thu>.jpg", save=True)        # xem bằng mắt
```

Nếu phiên bị ngắt giữa chừng:
```python
model = YOLO("/content/drive/MyDrive/yolo/duong/weights/last.pt")
model.train(resume=True)
```

**Chỉ số cần đạt cho demo:** mAP50 ≥ 0.5; kiểm tra bằng mắt không nhầm bóng cây, vệt sơn thành ổ gà.

### 7.3 Script mô phỏng xe có camera hành trình

Cài đặt trên laptop: `pip install ultralytics opencv-python supabase`

```python
"""xe_camera_hanh_trinh.py — Mô phỏng một xe có camera hành trình gửi sự cố lên Supabase."""
import math
import cv2
from ultralytics import YOLO
from supabase import create_client

SUPABASE_URL = "https://<du-an>.supabase.co"
SUPABASE_ANON_KEY = "<khoa-anon>"
MODEL = "best.pt"
VIDEO = "duong_can_tho.mp4"
STRIDE = 5                            # xử lý 1 trên 5 khung hình
CONF = 0.55                           # ngưỡng độ tin cậy
DEDUP_M = 25                          # bán kính chống gửi trùng (mét)
MUC_DO = {"flood": 3, "pothole": 2}   # lớp được gửi và mức độ

# Tuyến mô phỏng xe đi qua, dạng (vĩ độ, kinh độ)
TUYEN = [(10.0301, 105.7712), (10.0325, 105.7780),
         (10.0341, 105.7880), (10.0362, 105.7955)]


def vi_tri_theo_tien_do(t: float) -> tuple[float, float]:
    """t từ 0 (đầu video) đến 1 (cuối video) → tọa độ trên tuyến mô phỏng."""
    t = min(max(t, 0.0), 1.0)
    doan = t * (len(TUYEN) - 1)
    i = min(int(doan), len(TUYEN) - 2)
    f = doan - i
    (a_lat, a_lon), (b_lat, b_lon) = TUYEN[i], TUYEN[i + 1]
    return a_lat + (b_lat - a_lat) * f, a_lon + (b_lon - a_lon) * f


def cach_nhau_met(p, q) -> float:
    """Khoảng cách xấp xỉ (mét) giữa hai điểm (vĩ độ, kinh độ) gần nhau."""
    dy = (p[0] - q[0]) * 111_320
    dx = (p[1] - q[1]) * 111_320 * math.cos(math.radians(p[0]))
    return math.hypot(dx, dy)


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    model = YOLO(MODEL)
    tong_khung = int(cv2.VideoCapture(VIDEO).get(cv2.CAP_PROP_FRAME_COUNT))
    da_gui: list[tuple[str, tuple[float, float]]] = []

    ket_qua = model.predict(VIDEO, stream=True, conf=CONF,
                            vid_stride=STRIDE, show=True, verbose=False)
    for i, r in enumerate(ket_qua):
        vi_tri = vi_tri_theo_tien_do(i * STRIDE / max(tong_khung - 1, 1))
        for box in r.boxes:
            loai = model.names[int(box.cls)]
            if loai not in MUC_DO:
                continue
            if any(l == loai and cach_nhau_met(vi_tri, p) < DEDUP_M for l, p in da_gui):
                continue
            try:
                sb.rpc("bao_cao_su_co", {
                    "p_loai": loai, "p_muc_do": MUC_DO[loai],
                    "p_lat": vi_tri[0], "p_lon": vi_tri[1],
                }).execute()
                da_gui.append((loai, vi_tri))
                print(f"[GỬI] {loai} ({float(box.conf):.2f}) tại {vi_tri[0]:.5f}, {vi_tri[1]:.5f}")
            except Exception as e:
                print(f"[LỖI] {e}")


if __name__ == "__main__":
    main()
```

**Nguồn video:** quay vài phút bằng điện thoại gắn trên xe (không cần gán nhãn). Dự phòng: ghép ảnh trong thư mục `test/` của dataset thành chuỗi trình chiếu.

**Lưu ý:** laptop **không cần GPU** — chỉ train mới cần. Model nano chạy trên CPU với `vid_stride=5` là đủ.

### 7.4 Tiêu chí hoàn thành luồng A

- [ ] Có `best.pt` lưu trên Google Drive, mAP50 ≥ 0.5
- [ ] `model.names` chứa đúng `pothole` và `flood`
- [ ] Chạy script: cửa sổ hiện video với khung nhận diện
- [ ] Mỗi sự cố chỉ được gửi một lần; dòng mới xuất hiện trong Supabase Table Editor

---

## 8. Luồng B — Cloud

**Mục tiêu:** Kho sự cố chung trên Supabase với hai hàm API, bảo mật và đẩy thời gian thực.

### 8.1 Tạo dự án

- Tạo dự án Supabase, chọn vùng **Singapore** (không đổi được về sau).
- Ghi lại `Project URL` và khóa `anon`. **Không bao giờ** đặt khóa `service_role` vào app hay script.

### 8.2 Toàn bộ SQL (chạy trong SQL Editor)

```sql
-- 1. Bật PostGIS
create extension if not exists postgis;

-- 2. Bảng sự cố
create table if not exists su_co (
  id          bigserial primary key,
  loai        text not null check (loai in ('pothole', 'flood')),
  muc_do      smallint not null check (muc_do between 1 and 3),
  vi_tri      geography(point, 4326) not null,   -- đơn vị khoảng cách: mét
  so_bao_cao  int not null default 1,
  lan_dau     timestamptz not null default now(),
  lan_cuoi    timestamptz not null default now(),
  het_han     timestamptz not null
);
create index if not exists su_co_vi_tri_idx on su_co using gist (vi_tri);
create index if not exists su_co_het_han_idx on su_co (het_han);

-- 3. Hàm ghi: gộp sự cố cùng loại trong 25 m, tạo mới nếu chưa có
create or replace function bao_cao_su_co(
  p_loai text, p_muc_do int, p_lat float8, p_lon float8
)
returns void
language plpgsql
security definer                 -- chạy với quyền người tạo hàm (vượt RLS có kiểm soát)
set search_path = public
as $$
declare
  p        geography := st_setsrid(st_makepoint(p_lon, p_lat), 4326)::geography;
  thoi_han interval  := case when p_loai = 'flood' then interval '4 hours'
                             else interval '60 days' end;
begin
  update su_co
     set so_bao_cao = so_bao_cao + 1,
         muc_do     = greatest(muc_do, p_muc_do),
         lan_cuoi   = now(),
         het_han    = greatest(het_han, now() + thoi_han)
   where id = (select id from su_co
                where loai = p_loai and het_han > now()
                  and st_dwithin(vi_tri, p, 25)
                order by vi_tri <-> p
                limit 1);

  if not found then
    insert into su_co (loai, muc_do, vi_tri, het_han)
    values (p_loai, p_muc_do, p, now() + thoi_han);
  end if;
end $$;

-- 4. Hàm đọc: sự cố còn hạn trong bán kính
create or replace function su_co_gan_day(
  p_lat float8, p_lon float8, p_ban_kinh int default 10000
)
returns table (id bigint, loai text, muc_do smallint,
               lat float8, lon float8, so_bao_cao int)
language sql stable
as $$
  select s.id, s.loai, s.muc_do,
         st_y(s.vi_tri::geometry) as lat,
         st_x(s.vi_tri::geometry) as lon,
         s.so_bao_cao
    from su_co s
   where s.het_han > now()
     and st_dwithin(s.vi_tri,
                    st_setsrid(st_makepoint(p_lon, p_lat), 4326)::geography,
                    p_ban_kinh);
$$;

-- 5. Bảo mật: ai cũng đọc được; không ai ghi trực tiếp — chỉ ghi qua bao_cao_su_co
alter table su_co enable row level security;
drop policy if exists doc_cong_khai on su_co;
create policy doc_cong_khai on su_co for select using (true);

-- 6. Bật Realtime cho bảng
alter publication supabase_realtime add table su_co;
```

### 8.3 Kiểm tra nhanh

```sql
select bao_cao_su_co('flood', 3, 10.0341, 105.7880);
select bao_cao_su_co('flood', 3, 10.03411, 105.78801);   -- trong 25 m → so_bao_cao = 2
select * from su_co_gan_day(10.0341, 105.7880);
```

### 8.4 Tiêu chí hoàn thành luồng B

- [ ] Hai lệnh `bao_cao_su_co` gần nhau chỉ tạo **một** dòng với `so_bao_cao = 2`
- [ ] `su_co_gan_day` trả đúng sự cố, đúng `lat`, `lon`
- [ ] Script Python gửi thành công bằng khóa `anon`
- [ ] Dùng khóa `anon` ghi thẳng vào bảng (không qua hàm) bị từ chối
- [ ] Lưu ý vận hành: dự án miễn phí **tạm dừng sau 7 ngày không hoạt động** — chạy thử một ngày trước khi thi

---

## 9. Luồng C — App người nhận

**Mục tiêu:** App Flutter hiện bản đồ, vị trí xe, lộ trình; nhận sự cố từ cloud; cảnh báo đúng tuyến; đổi tuyến khi đường phía trước không đi được.

### 9.1 Cài đặt

```bash
flutter doctor                         # chạy đầu tiên, xử lý hết lỗi
flutter create canh_bao_duong
cd canh_bao_duong
flutter pub add maplibre_gl geolocator supabase_flutter sqflite path flutter_tts http
```

Sau khi cài, **không nâng cấp plugin giữa chừng**. Nếu plugin báo yêu cầu phiên bản Android tối thiểu cao hơn, sửa `minSdk` trong `android/app/build.gradle`.

Quyền trong `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

### 9.2 Cấu trúc thư mục

```
lib/
├── main.dart                        # khởi tạo Supabase, SQLite, mở màn hình bản đồ
├── mo_hinh/
│   ├── vi_tri.dart                  # lớp ViTri
│   └── su_co.dart                   # lớp SuCo
├── dich_vu/
│   ├── nguon_vi_tri.dart            # vị trí thật / mô phỏng
│   ├── kho_cuc_bo.dart              # SQLite
│   ├── kho_cloud.dart               # Supabase: prefetch, Realtime
│   ├── tim_duong.dart               # OpenRouteService
│   └── giong_noi.dart               # flutter_tts
├── logic/
│   ├── hinh_hoc.dart                # chia nhỏ tuyến, vùng tròn, khoảng cách dọc tuyến
│   ├── hanh_lang.dart               # lọc sự cố theo tuyến
│   ├── quyet_dinh_canh_bao.dart     # chọn cấp cảnh báo
│   └── doi_tuyen.dart               # đổi tuyến, chống dao động, chệch tuyến
└── giao_dien/
    ├── man_hinh_ban_do.dart
    └── dai_thong_bao.dart
```

### 9.3 Luồng dữ liệu trong app

```
Stream<ViTri> (thật hoặc mô phỏng)
   │ mỗi giây
   ├─► vẽ xe trên bản đồ, camera bám theo
   ├─► kiểm tra chệch tuyến
   └─► quyết định cảnh báo ──► dải thông báo / giọng nói / đổi tuyến

Đặt điểm đến (nhấn giữ bản đồ)
   └─► gọi OpenRouteService ─► chia nhỏ tuyến ─► lọc hành lang ─► vẽ tuyến + sự cố

Bắt đầu chuyến, mỗi 5 phút, hoặc Realtime báo có thay đổi
   └─► gọi su_co_gan_day ─► ghi SQLite ─► lọc hành lang ─► vẽ sự cố
```

### 9.4 Vị trí: kiểu `ViTri` và chế độ mô phỏng

Trong phòng thi điện thoại nằm yên trên bàn, nên app **bắt buộc** có chế độ mô phỏng cho xe tự chạy dọc lộ trình. Mọi logic chỉ nhận `Stream<ViTri>`.

```dart
class ViTri {
  final double lat, lon;     // vĩ độ, kinh độ
  final double huong;        // độ, 0 = bắc, 90 = đông
  final double tocDo;        // mét/giây
  final double saiSo;        // mét
  const ViTri(this.lat, this.lon, this.huong, this.tocDo, [this.saiSo = 5]);
}

// Nguồn thật
Stream<ViTri> viTriThat() => Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.bestForNavigation, distanceFilter: 5),
    ).map((p) => ViTri(p.latitude, p.longitude, p.heading, p.speed, p.accuracy));

// Nguồn mô phỏng: chạy dọc tuyến [[kinh độ, vĩ độ], ...], mỗi giây một bước
Stream<ViTri> viTriMoPhong(List<List<double>> tuyen, {double tocDo = 8.3}) async* {
  for (int i = 0; i < tuyen.length - 1; i++) {
    final a = tuyen[i], b = tuyen[i + 1];
    final dai = Geolocator.distanceBetween(a[1], a[0], b[1], b[0]);
    final huong = Geolocator.bearingBetween(a[1], a[0], b[1], b[0]);
    final soBuoc = (dai / tocDo).ceil().clamp(1, 1000);
    for (int k = 0; k < soBuoc; k++) {
      final f = k / soBuoc;
      yield ViTri(a[1] + (b[1] - a[1]) * f, a[0] + (b[0] - a[0]) * f, huong, tocDo);
      await Future.delayed(const Duration(seconds: 1));
    }
  }
}
```

Quy tắc với vị trí thật: bỏ qua vị trí có `saiSo > 30`; khi `tocDo < 1.5` giữ nguyên hướng đáng tin cuối cùng.

### 9.5 SQLite: ba bảng

```dart
final db = await openDatabase('canh_bao.db', version: 1, onCreate: (db, _) async {
  // Bản sao sự cố khu vực, tải từ Supabase
  await db.execute('''CREATE TABLE su_co_khu_vuc (
    id INTEGER PRIMARY KEY, loai TEXT, muc_do INTEGER,
    lat REAL, lon REAL, so_bao_cao INTEGER)''');
  // Nhật ký đã cảnh báo, để không nhắc lại trong 12 giờ
  await db.execute('''CREATE TABLE da_canh_bao (
    su_co_id INTEGER, thoi_gian TEXT)''');
  // Cài đặt: điểm đến gần nhất, chế độ mô phỏng...
  await db.execute('''CREATE TABLE cai_dat (khoa TEXT PRIMARY KEY, gia_tri TEXT)''');
});
```

Khi ghi nhiều dòng (sau prefetch), dùng `db.batch()` để ghi một lần.

Ghi chú: trong bản demo app **chỉ nhận**, không gửi sự cố, nên không cần bảng hàng đợi gửi. Bảng này thuộc thiết bị nguồn trong hệ thống thật.

### 9.6 Supabase: prefetch và Realtime

```dart
await Supabase.initialize(url: '<Project URL>', anonKey: '<khoa anon>');
final cloud = Supabase.instance.client;

Future<void> prefetch(ViTri v) async {
  final ds = await cloud.rpc('su_co_gan_day',
      params: {'p_lat': v.lat, 'p_lon': v.lon}) as List;
  await khoCucBo.thayTheSuCoKhuVuc(ds);     // xóa cũ, ghi mới bằng batch
  await capNhatHanhLangVaBanDo();
}

void dangKyRealtime() {
  cloud
      .channel('su_co_thay_doi')
      .onPostgresChanges(
        event: PostgresChangeEvent.all,
        schema: 'public',
        table: 'su_co',
        callback: (_) => henGioPrefetch(),   // chỉ dùng làm tín hiệu
      )
      .subscribe();
}
```

**Quyết định:** Realtime chỉ dùng làm **tín hiệu "có thay đổi"**, sau đó app gọi lại `su_co_gan_day`. Lý do: bản ghi Realtime gửi cột `vi_tri` ở dạng mã nhị phân của PostGIS, không phải vĩ độ/kinh độ. `henGioPrefetch()` gộp nhiều tín hiệu liên tiếp trong 1 giây thành một lần gọi.

### 9.7 Bản đồ

**Style nền:** `https://tiles.openfreemap.org/styles/liberty` (miễn phí, không cần khóa, dữ liệu OpenStreetMap). Vị trí khởi đầu: `LatLng(10.0341, 105.7880)`, zoom 14.

**Nguồn và lớp** — tạo trong `onStyleLoadedCallback`, thêm theo thứ tự từ dưới lên:

| Nguồn | Lớp | Kiểu | Cách vẽ |
|---|---|---|---|
| `lo-trinh-cu` | `lop-lo-trinh-cu` | line | `#B4B2A9`, rộng 4, nét đứt `[2, 2]` |
| `lo-trinh` | `lop-lo-trinh` | line | `#1D9E75`, rộng 6, đầu tròn |
| `su-co` | `lop-su-co` | circle | Màu: `flood` `#378ADD`, `pothole` `#EF9F27` · Bán kính: mức 3 → 11, mức 2 → 8, khác → 5 · Độ đậm: `tren_tuyen` → 1.0, không → 0.35 · Viền trắng 2 |
| `xe` | `lop-xe` | circle | `#0F6E56`, bán kính 9, viền trắng 3 |

```dart
await m.addCircleLayer('su-co', 'lop-su-co', const CircleLayerProperties(
  circleColor: ['match', ['get', 'loai'], 'flood', '#378ADD', 'pothole', '#EF9F27', '#888780'],
  circleRadius: ['match', ['get', 'muc_do'], 3, 11, 2, 8, 5],
  circleOpacity: ['case', ['==', ['get', 'tren_tuyen'], true], 1.0, 0.35],
  circleStrokeColor: '#FFFFFF',
  circleStrokeWidth: 2,
));
```

**Tương tác:**
- Nhấn giữ bản đồ (`onMapLongClick`) → đặt điểm đến → tính lộ trình
- Camera bám xe: zoom 16, nghiêng 45°, xoay theo hướng xe khi `tocDo > 1.5`
- Chạm bản đồ → ngừng bám; nút định vị → bám lại
- Chỉ gọi `setGeoJsonSource` cho sự cố khi danh sách thay đổi; vị trí xe cập nhật mỗi giây

### 9.8 Hình học: chia nhỏ tuyến, khoảng cách dọc tuyến, vùng tròn

Lộ trình từ OpenRouteService chỉ có điểm ở các khúc cua; đoạn thẳng dài có thể không có điểm nào. **Phải chia nhỏ** trước khi lọc hành lang, nếu không sự cố nằm giữa đoạn thẳng sẽ bị coi là "ngoài tuyến".

```dart
/// Chèn điểm để hai điểm liên tiếp cách nhau không quá [buoc] mét.
List<List<double>> chiaNhoTuyen(List<List<double>> tuyen, {double buoc = 10}) {
  final kq = <List<double>>[tuyen.first];
  for (int i = 0; i < tuyen.length - 1; i++) {
    final a = tuyen[i], b = tuyen[i + 1];
    final d = Geolocator.distanceBetween(a[1], a[0], b[1], b[0]);
    final n = (d / buoc).ceil().clamp(1, 10000);
    for (int k = 1; k <= n; k++) {
      final f = k / n;
      kq.add([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]);
    }
  }
  return kq;
}

/// Chỉ số điểm gần nhất trên tuyến và khoảng cách tới đó (mét).
(int, double) diemGanNhat(List<List<double>> tuyen, double lat, double lon) {
  var chiSo = 0;
  var min = double.infinity;
  for (int i = 0; i < tuyen.length; i++) {
    final d = Geolocator.distanceBetween(tuyen[i][1], tuyen[i][0], lat, lon);
    if (d < min) { min = d; chiSo = i; }
  }
  return (chiSo, min);
}

/// Khoảng cách dọc tuyến giữa hai chỉ số (mét).
double khoangCachDocTuyen(List<List<double>> tuyen, int tu, int den) {
  double tong = 0;
  for (int i = tu; i < den; i++) {
    tong += Geolocator.distanceBetween(
        tuyen[i][1], tuyen[i][0], tuyen[i + 1][1], tuyen[i + 1][0]);
  }
  return tong;
}

/// Đa giác 12 cạnh bán kính [banKinh] mét, chuẩn GeoJSON, điểm đầu = điểm cuối.
List<List<double>> vungTron(double lat, double lon, {double banKinh = 40}) {
  final dLat = banKinh / 111320;
  final dLon = banKinh / (111320 * cos(lat * pi / 180));
  final diem = <List<double>>[
    for (int i = 0; i < 12; i++)
      [lon + dLon * cos(2 * pi * i / 12), lat + dLat * sin(2 * pi * i / 12)]
  ];
  return [...diem, diem.first];
}
```

### 9.9 Lọc hành lang

Chạy **mỗi khi có lộ trình mới hoặc danh sách sự cố thay đổi** (không chạy mỗi giây):

```
với mỗi sự cố s:
    (chiSo, d) = diemGanNhat(tuyenDaChiaNho, s.lat, s.lon)
    s.tren_tuyen = (d <= 30)
    s.chi_so_tren_tuyen = chiSo
```

Trong lúc chạy, sự cố **liên quan** = `tren_tuyen` **và** `chi_so_tren_tuyen > chiSoXe`.

**Chế độ tự do** (chưa đặt điểm đến): sự cố liên quan = nằm trong nón `±35°` quanh hướng xe **và** cách xe (đường thẳng) không quá ngưỡng cảnh báo. Chế độ tự do không đổi tuyến.

### 9.10 Quyết định cảnh báo

"**Cấp cảnh báo**" (cách thông báo cho tài xế) khác với "**mức độ**" (độ nghiêm trọng của sự cố):

| Cấp | Hình thức | Điều kiện |
|---|---|---|
| **0 — Im lặng** | Chỉ chấm trên bản đồ | Sự cố ngoài tuyến, hoặc `muc_do = 1` |
| **1 — Hình ảnh** | Dải thông báo | Sự cố liên quan, `muc_do ≥ 2`, còn cách ≤ 500 m dọc tuyến |
| **2 — Giọng nói** | Đọc + dải thông báo | Sự cố liên quan, `muc_do ≥ 2`, còn cách ≤ `tocDo × 9 + 30` m |
| **3 — Đổi tuyến** | Đọc + vẽ tuyến mới | Sự cố liên quan, `muc_do = 3`, còn cách > 150 m, được phép đổi tuyến |

Quy tắc bổ sung:
- `muc_do = 3` nhưng còn cách ≤ 150 m → không đổi tuyến, chỉ cấp 2: *"Phía trước ngập sâu, giảm tốc độ"*
- Không đọc lại sự cố đã có trong `da_canh_bao` trong 12 giờ
- Tối đa một câu đọc mỗi 45 giây; nhiều sự cố gần nhau gộp thành một câu
- Câu đọc tối đa khoảng 10 từ, ví dụ: *"Phía trước 120 mét, ổ gà lớn"*
- **Tóm tắt đầu chuyến** khi vừa có lộ trình: *"Tuyến của bạn có 1 đoạn ngập và 3 ổ gà"*

### 9.11 Đổi tuyến

1. Lấy các sự cố `muc_do = 3` còn hạn, gần xe nhất, **tối đa 20 sự cố**.
2. Tạo `vungTron(lat, lon, banKinh: 40)` cho mỗi sự cố.
3. Gọi OpenRouteService từ **vị trí hiện tại** đến điểm đến, kèm tất cả vùng né trong **một** yêu cầu.
4. Thành công → chia nhỏ tuyến mới → lọc hành lang lại → tuyến cũ chuyển sang nguồn `lo-trinh-cu` → đọc: *"Phía trước ngập sâu. Đã đổi tuyến, dài thêm X mét."*
5. Thất bại → giữ tuyến cũ, đọc: *"Không tìm được tuyến khác. Phía trước ngập sâu."*
6. Chống dao động: cách lần đổi tuyến trước ít nhất 2 phút.

**Yêu cầu OpenRouteService:**

```
POST https://api.openrouteservice.org/v2/directions/driving-car/geojson
Authorization: <khoa ORS>
Content-Type: application/json

{
  "coordinates": [[lon_xe, lat_xe], [lon_dich, lat_dich]],
  "options": {
    "avoid_polygons": {
      "type": "MultiPolygon",
      "coordinates": [ [ <vungTron 1> ], [ <vungTron 2> ] ]
    }
  }
}
```

- Chỉ thêm `options` khi có ít nhất một vùng né
- Kết quả: `features[0].geometry.coordinates` (lộ trình `[kinh độ, vĩ độ]`), `features[0].properties.summary.distance` (mét), `.duration` (giây)
- Dùng profile `driving-car` (không có profile xe máy)
- **Nâng cao (tùy chọn):** xin thêm tuyến thay thế và chấm điểm = thời gian + phạt sự cố trên tuyến (ngập nông +3 phút, ổ gà lớn +30 giây); nếu API báo tổ hợp tham số không hỗ trợ, giữ cách làm cơ bản ở trên

### 9.12 Chệch tuyến

```
nếu khoảng cách từ xe đến điểm gần nhất trên tuyến > 40 m liên tục 6 giây:
    hủy mọi cảnh báo đang chờ của tuyến cũ
    tạm chuyển sang chế độ tự do
    gọi OpenRouteService tính tuyến mới từ vị trí hiện tại đến điểm đến
```

### 9.13 Giọng nói

```dart
final tts = FlutterTts();
await tts.setLanguage('vi-VN');
await tts.setSpeechRate(0.5);
await tts.awaitSpeakCompletion(true);

Future<void> doc(String cau) async {
  await tts.stop();          // không chồng câu
  await tts.speak(cau);
}
```

Kiểm tra `await tts.isLanguageAvailable('vi-VN')` trên **đúng điện thoại demo**. Nếu thiếu: *Cài đặt → Ngôn ngữ → Chuyển văn bản thành giọng nói* → tải gói tiếng Việt.

### 9.14 Tiêu chí hoàn thành luồng C

- [ ] Bản đồ OpenFreeMap hiện Cần Thơ trên điện thoại thật
- [ ] Chấm xe di chuyển (GPS thật và chế độ mô phỏng)
- [ ] Prefetch vẽ đúng sự cố; sự cố do laptop gửi hiện lên trong vài giây
- [ ] Nhấn giữ đặt điểm đến → lộ trình hiện
- [ ] Sự cố ngoài tuyến bị làm mờ
- [ ] Xe mô phỏng đến gần sự cố → đọc cảnh báo tiếng Việt đúng khoảng cách
- [ ] Gặp ngập sâu phía trước → tuyến mới hiện, tuyến cũ nét đứt, có câu thông báo

---

## 10. Lịch triển khai 10 ngày

| Ngày | Luồng A — AI | Luồng B — Cloud | Luồng C — App | Mốc kiểm tra cuối ngày |
|---|---|---|---|---|
| **1** | Chốt hợp đồng dữ liệu (cả nhóm, 30 phút) · Colab + Roboflow: train thử | Tạo dự án Supabase, chạy toàn bộ SQL mục 8.2 | `flutter doctor` sạch lỗi · Bản đồ hiện trên điện thoại | Có `best.pt` đầu tiên · Hàm SQL chạy được · Bản đồ chạy |
| **2** | Gộp dataset, đổi tên lớp, train đầy đủ · **Quay video đường** | Script Python gửi thử 5 sự cố giả | `ViTri`, nguồn thật + mô phỏng · Chấm xe, camera bám | Sự cố giả trong Table Editor · Xe mô phỏng chạy trên bản đồ |
| **3** | Đánh giá, xem ảnh kết quả, chạy lên video tự quay | Hỗ trợ C | SQLite · Prefetch → vẽ sự cố | Laptop hiện khung nhận diện · Sự cố giả hiện trên điện thoại |
| **4** | Hoàn thiện script mục 7.3 | Hỗ trợ C | Realtime → prefetch lại | **MỐC 1 — XƯƠNG SỐNG:** video trên laptop → vài giây sau chấm mới trên điện thoại |
| **5** | Train lại nếu model yếu · Chọn đoạn video tốt nhất | Hỗ trợ C | Đặt điểm đến → ORS → chia nhỏ tuyến → lọc hành lang | Lộ trình hiện, sự cố ngoài tuyến mờ |
| **6** | Hỗ trợ C | Hỗ trợ C | Quyết định cảnh báo 4 cấp · TTS tiếng Việt · Dải thông báo | Xe mô phỏng đến gần → đọc cảnh báo |
| **7** | Hỗ trợ C | Hỗ trợ C | Đổi tuyến · Chống dao động · Chệch tuyến · Tuyến cũ nét đứt | **MỐC 2 — TRỌN LUỒNG DEMO:** laptop phát hiện ngập → điện thoại cảnh báo và đổi tuyến |
| **8** | **Dự phòng:** sửa lỗi, chạy thử toàn bộ 10 lần liên tiếp | | | 10 lần không lỗi |
| **9** | Quay video demo dự phòng · Slide · Sơ đồ kiến trúc | | | Video 2–3 phút chạy không cần mạng |
| **10** | Luyện thuyết trình 3 lần · Chuẩn bị hỏi đáp · Kiểm tra lần cuối | | | Sẵn sàng |

**Nguyên tắc:** đạt Mốc 1 (xương sống) trước khi làm tính năng. Nếu trễ, cắt theo thứ tự: tóm tắt đầu chuyến → chống dao động → chệch tuyến → đổi tuyến. **Không cắt** cảnh báo giọng nói.

---

## 11. Thứ tự bắt đầu và phân công

### 11.1 Thứ tự tìm hiểu

| Thứ tự | Việc | Lý do |
|---|---|---|
| 1 | **Luồng A** — train model đầu tiên trên Colab | Cốt lõi của cuộc thi, rủi ro cao nhất, không phụ thuộc gì |
| song song | **Cài Flutter + Android Studio** | Tải nặng, lỗi khó đoán — cần chạy nền từ sớm |
| 2 | **Luồng B** — Supabase | Nhỏ nhất (khoảng nửa ngày); cần có để A gửi, C nhận |
| 3 | **Luồng C** — App | Nặng nhất; làm khi đã hiểu dữ liệu |

Buổi đầu tiên, **cả nhóm cùng chạy luồng A một lần** (1–2 giờ) để ai cũng thấy model trả ra dữ liệu gì.

### 11.2 Phân công

| Số người | Cách chia |
|---|---|
| 3 | Mỗi người một luồng; người làm B chuyển sang C từ ngày 3 |
| 2 | Người 1: A + B (Python, SQL) · Người 2: C |
| 1 | Tuần tự theo các mốc; ưu tiên đạt Mốc 1 trước ngày 5 |

---

## 12. Rủi ro và phương án dự phòng

| Rủi ro | Dấu hiệu sớm | Phương án |
|---|---|---|
| Cài Flutter không xong | Hết ngày 1 `flutter doctor` còn lỗi | Nhờ người có kinh nghiệm ngay ngày 2 |
| Model nhận diện kém trên video tự quay | mAP thấp, bỏ sót nhiều | Dùng ảnh `test/` của Roboflow làm đầu vào demo |
| Laptop không có GPU | — | Không ảnh hưởng: chỉ train cần GPU |
| Colab ngắt phiên, mất kết quả | — | Luôn lưu vào Google Drive; `resume=True` |
| Colab hết hạn mức GPU | Không được cấp GPU | Chuyển sang Kaggle Notebooks |
| Supabase tạm dừng | Không kết nối được | Mở dự án một ngày trước thi |
| OpenRouteService lỗi, hết hạn mức | Lỗi `429`, `5xx` | Lưu sẵn một tuyến né GeoJSON trong app làm dự phòng |
| Không có giọng tiếng Việt | TTS đọc giọng Anh | Cài gói giọng ngay ngày 6 trên đúng máy demo |
| Mạng phòng thi yếu | — | Mang điện thoại phát Wi-Fi; có video demo dự phòng |

---

## 13. Danh sách bẫy kỹ thuật

**Tọa độ**
- [ ] GeoJSON và ORS: `[kinh độ, vĩ độ]`; `LatLng`: `(vĩ độ, kinh độ)`; `ST_MakePoint(kinh độ, vĩ độ)`
- [ ] Dấu hiệu nhầm: điểm hiện giữa biển hoặc sai châu lục

**AI**
- [ ] Nạp `yolo11n.pt`, không phải `yolo11n.yaml`
- [ ] Tên lớp chữ thường, thống nhất sau khi gộp dataset
- [ ] Bật GPU trên Colab, kiểm tra bằng `!nvidia-smi`
- [ ] Lưu kết quả train vào Google Drive
- [ ] Xem ảnh kết quả bằng mắt, không chỉ nhìn mAP

**Cloud**
- [ ] Hàm ghi có `security definer`, nếu không sẽ bị RLS chặn
- [ ] Đã bật Realtime cho bảng (`alter publication ...`)
- [ ] Khóa `service_role` không nằm trong app hay script
- [ ] Dự án không bị tạm dừng trước ngày thi

**App**
- [ ] Thêm nguồn và lớp bản đồ trong `onStyleLoadedCallback`, không phải `onMapCreated`
- [ ] Bản đồ nằm trong vùng có kích thước xác định (thân `Scaffold` hoặc `Expanded`)
- [ ] Chia nhỏ tuyến trước khi lọc hành lang
- [ ] Không dùng `heading` khi `tocDo < 1.5`
- [ ] `tts.stop()` trước mỗi câu mới
- [ ] Đã khai báo quyền internet và vị trí
- [ ] Không dùng máy chủ ảnh bản đồ của openstreetmap.org trong app

---

## 14. Kịch bản demo (3 phút)

| Thời lượng | Hành động | Giám khảo thấy |
|---|---|---|
| 30 giây | Điện thoại: nhấn giữ đặt điểm đến, bật chế độ mô phỏng | Lộ trình xanh, xe bắt đầu chạy |
| 45 giây | Laptop: chạy video "camera hành trình" | Khung nhận diện quanh ổ gà, rồi vùng ngập |
| 45 giây | Chỉ vào điện thoại | Chấm sự cố lần lượt hiện; trên tuyến thì đậm, ngoài tuyến thì mờ |
| 45 giây | Xe mô phỏng đến gần vùng ngập | App đọc cảnh báo; tuyến cũ nét đứt, tuyến mới hiện ra |
| 15 giây | Kết luận | *Một xe có camera vừa giúp một người chưa từng đi qua đoạn đó tránh được vùng ngập* |

Khi trình bày, nói rõ phần **đã chạy thật** (model AI, luồng dữ liệu qua cloud, lọc theo tuyến, cảnh báo, đổi tuyến) và phần **mô phỏng** (GPS của xe nguồn, nguồn video, vị trí người nhận).

---

## 15. Hướng phát triển hệ thống thật

| Hạng mục | Bản demo | Hệ thống thật |
|---|---|---|
| Nguồn dữ liệu | Laptop phát video | Camera hành trình có chip AI trên xe taxi, xe công nghệ, xe buýt |
| Dữ liệu train | Dataset công khai | Ảnh thu thập tại Việt Nam, chọn lọc ảnh model còn lưỡng lự (active learning) |
| Vòng lặp model | Train một lần | Train lại định kỳ hàng tháng, cập nhật xuống thiết bị |
| Quyền riêng tư ảnh | — | Làm mờ khuôn mặt, biển số **ngay trên thiết bị** trước khi gửi |
| Quyền riêng tư vị trí | — | Làm thô tọa độ bằng lưới H3; bỏ 400 m đầu/cuối hành trình; không gắn định danh |
| Độ tin cậy | Một báo cáo là đủ | Cần ≥ 3 thiết bị khác nhau xác nhận; người dùng xác nhận "còn / đã hết" |
| Backend | Supabase | Tự vận hành: API + PostgreSQL/PostGIS + hàng đợi + cache; đặt tại Việt Nam |
| Tìm đường | ORS công cộng, né tuyệt đối | Tự vận hành (GraphHopper/ORS), tăng trọng số cạnh thay vì né tuyệt đối |
| Người dùng | Android | Android, iOS; chạy nền |
| Quản lý | — | Web dashboard bản đồ nhiệt cho cơ quan giao thông |

**Pháp lý:** vị trí cá nhân xác định qua dịch vụ định vị là **dữ liệu cá nhân nhạy cảm** theo Luật Bảo vệ dữ liệu cá nhân 2025 (Luật số 91/2025/QH15) và Nghị định 356/2025/NĐ-CP, cùng có hiệu lực từ 01/01/2026. Hệ thống thật cần: sự đồng ý riêng biệt, đánh giá tác động xử lý dữ liệu, biện pháp khử nhận dạng, cân nhắc quy định chuyển dữ liệu ra nước ngoài.

---

## 16. Tài liệu tham khảo

| Công nghệ | Tài liệu |
|---|---|
| Ultralytics YOLO | https://docs.ultralytics.com |
| Roboflow Universe | https://universe.roboflow.com |
| Dataset ổ gà (gợi ý) | https://universe.roboflow.com/intel-unnati-training-program/pothole-detection-bqu6s |
| Google Colab | https://colab.research.google.com |
| Supabase | https://supabase.com/docs |
| Flutter | https://docs.flutter.dev |
| maplibre_gl | https://pub.dev/packages/maplibre_gl |
| MapLibre Style Spec | https://maplibre.org/maplibre-style-spec |
| OpenFreeMap | https://openfreemap.org |
| OpenRouteService | https://openrouteservice.org |
| geolocator | https://pub.dev/packages/geolocator |
| flutter_tts | https://pub.dev/packages/flutter_tts |
| sqflite | https://pub.dev/packages/sqflite |
| supabase_flutter | https://pub.dev/packages/supabase_flutter |

---

## 17. Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| Model | File chứa kiến thức AI đã học (`best.pt`) |
| Dataset | Bộ ảnh kèm nhãn vị trí vật thể |
| Train | Quá trình dạy model |
| Fine-tune | Dạy thêm một model đã học sẵn cho việc mới |
| Inference / nhận diện | Dùng model đã học để tìm vật thể trong ảnh mới |
| Epoch | Một lượt model học hết toàn bộ dataset |
| Confidence | Độ tự tin của model cho một phát hiện, 0–1 |
| Precision | Trong các lần báo "có", bao nhiêu lần đúng |
| Recall | Trong các sự cố thật, tìm ra được bao nhiêu |
| mAP50 | Điểm tổng hợp độ chính xác; khung chồng ≥ 50% được tính là đúng |
| Overfitting | Model học vẹt: giỏi trên ảnh đã học, kém trên ảnh mới |
| GeoJSON | Định dạng chuẩn mô tả điểm, đường, vùng trên bản đồ |
| PostGIS | Phần mở rộng giúp PostgreSQL hiểu dữ liệu địa lý |
| RLS | Row Level Security — quy tắc ai được đọc, ghi dòng nào |
| Realtime | Cơ chế Supabase đẩy thay đổi xuống app qua WebSocket |
| Prefetch | Tải trước dữ liệu khu vực vào máy để dùng cục bộ |
| Hành lang tuyến | Dải ±30 m quanh lộ trình; sự cố trong dải mới được xét |
| Cấp cảnh báo | Cách thông báo cho tài xế (0 im lặng → 3 đổi tuyến) |
| Mức độ | Độ nghiêm trọng của sự cố (1 nhẹ → 3 không đi được) |
| Avoid polygons | Vùng gửi cho OpenRouteService để lộ trình tránh đi qua |
