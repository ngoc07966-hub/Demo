"""main.py — Backend demo web nhận diện sự cố giao thông.

Chạy:  uvicorn main:app --port 8000     (hoặc chạy script chay.ps1)
Mở:    http://localhost:8000

Quy ước quan trọng: MỌI tọa độ trong file này là [kinh độ, vĩ độ] (chuẩn GeoJSON).
Chỉ khi gọi Supabase mới tách ra thành p_lat / p_lon.
"""
import asyncio
import base64
import json
import math
import os
import time
import uuid
from pathlib import Path

import cv2
import httpx
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO

GOC = Path(__file__).parent
load_dotenv(GOC / ".env")                 # đọc khóa ORS từ file .env nếu có

# Đổi file cấu hình bằng biến môi trường KICH_BAN — chay_thu.ps1 dùng cách này để
# chạy chế độ thử mà không phải sửa kich_ban.json thật.
TEP_KICH_BAN = GOC / os.environ.get("KICH_BAN", "kich_ban.json")
if not TEP_KICH_BAN.exists():
    raise SystemExit(f"Không tìm thấy file cấu hình: {TEP_KICH_BAN}")
KB = json.loads(TEP_KICH_BAN.read_text(encoding="utf-8"))
print(f"[Cấu hình] {TEP_KICH_BAN.name}" + ("  ← CHẾ ĐỘ THỬ" if KB.get("che_do_thu") else ""))

ORS_API_KEY = os.environ.get("ORS_API_KEY", "").strip()
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
THU_MUC_UPLOAD = GOC / "uploads"
THU_MUC_UPLOAD.mkdir(exist_ok=True)


# ─────────────────────────── Nạp model ───────────────────────────

def tim_model(ten: str) -> Path:
    """Tìm file model. Thứ tự: đường dẫn tuyệt đối → thư mục gốc → thư mục models/.

    Nhờ nhánh "thư mục gốc" mà cả hai cách khai trong kich_ban.json đều chạy:
        "model": "best.pt"                      → WebDemo\\best.pt
        "model": "models/v1-20260925/best.pt"   → thư mục phiên bản (xem models/README.md)

    Trả về nguyên tên nếu không thấy ở đâu cả — để Ultralytics tự tải các model
    chính thức (yolo11n.pt, yolov8n.pt...) về khi thử giao diện lúc chưa có best.pt.
    """
    p = Path(ten)
    if p.is_absolute():
        return p
    for thu_muc in (GOC, GOC / "models"):
        if (thu_muc / ten).exists():
            return thu_muc / ten
    return Path(ten)


def doc_thong_tin_model(duong_dan: Path):
    """Đọc model.json nằm CẠNH file model — thông tin bản train để hiện lên giao diện.

    Không có file thì bỏ qua, model vẫn chạy bình thường.
    """
    tep = duong_dan.parent / "model.json"
    if not tep.exists():
        return None
    try:
        return json.loads(tep.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Model] ⚠ Không đọc được {tep}: {e}")
        return None


def nap_model():
    """→ (model, thông tin bản train). Cả hai là None nếu không nạp được."""
    duong_dan = tim_model(KB["model"])
    try:
        m = YOLO(str(duong_dan))
        print(f"[Model] Đã nạp: {duong_dan}")
        print(f"[Model] Các lớp model biết: {m.names}")
        thieu = [l for l in KB["lop"] if l not in set(m.names.values())]
        if thieu:
            print(f"[Model] ⚠ Lớp khai trong kich_ban.json nhưng model KHÔNG có: {thieu}")
            print( "[Model]   → Sửa khóa trong mục 'lop' cho khớp danh sách ở trên.")

        tt = doc_thong_tin_model(duong_dan)
        if tt:
            print(f"[Model] Bản train: {tt.get('phien_ban', '?')} · {tt.get('ngay_train', '?')}"
                  + (f" · mAP50 {tt['mAP50']}" if tt.get("mAP50") is not None else ""))
            if tt.get("dataset"):
                print(f"[Model] Dataset:   {tt['dataset']}")
        else:
            print(f"[Model] (Chưa có {duong_dan.parent / 'model.json'} — xem models/README.md)")
        return m, tt
    except Exception as e:
        print(f"[Model] ✗ Không nạp được '{KB['model']}': {e}")
        print( "[Model]   Đã tìm ở:")
        print(f"[Model]     {GOC / KB['model']}")
        print(f"[Model]     {GOC / 'models' / KB['model']}")
        print( "[Model]   Train xong trên Colab thì thả best.pt vào một trong hai chỗ đó.")
        print( "[Model]   Muốn thử giao diện trước: đổi \"model\" thành \"yolo11n.pt\" trong kich_ban.json.")
        print( "[Model]   Phần bản đồ và định tuyến vẫn chạy bình thường.")
        return None, None


model, THONG_TIN_MODEL = nap_model()
app = FastAPI(title="Demo nhận diện sự cố giao thông")
app.mount("/static", StaticFiles(directory=GOC / "static"), name="static")

# Supabase — tùy chọn, bật trong kich_ban.json
sb = None
if KB.get("supabase", {}).get("bat"):
    from supabase import create_client
    sb = create_client(KB["supabase"]["url"], KB["supabase"]["anon_key"])


# ─────────────────────────── Hình học ───────────────────────────

def khoang_cach_m(a, b):
    """Khoảng cách (mét) giữa hai điểm [kinh độ, vĩ độ]."""
    R = 6_371_000
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def vi_tri_theo_tien_do(duong, t):
    """Vị trí trên đường [[kinh độ, vĩ độ], ...] ứng với tỉ lệ quãng đường t (0 → 1)."""
    t = min(max(t, 0.0), 1.0)
    if len(duong) < 2:
        return list(duong[0])
    doan = [khoang_cach_m(duong[i], duong[i + 1]) for i in range(len(duong) - 1)]
    con_lai = t * sum(doan)
    for i, d in enumerate(doan):
        if con_lai <= d or i == len(doan) - 1:
            f = 0.0 if d == 0 else min(con_lai / d, 1.0)
            a, b = duong[i], duong[i + 1]
            return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
        con_lai -= d
    return list(duong[-1])


def vung_tron(lon, lat, ban_kinh_m, so_canh=12):
    """Đa giác quanh một điểm, dùng cho avoid_polygons. Điểm đầu = điểm cuối."""
    d_lat = ban_kinh_m / 111_320
    d_lon = ban_kinh_m / (111_320 * math.cos(math.radians(lat)))
    diem = [[lon + d_lon * math.cos(2 * math.pi * i / so_canh),
             lat + d_lat * math.sin(2 * math.pi * i / so_canh)] for i in range(so_canh)]
    return diem + [diem[0]]


# ─────────────────────── Hành trình xe camera ───────────────────────

def lay_hanh_trinh_xe_camera():
    """Đường đi mô phỏng của xe có camera hành trình.

    Ưu tiên: danh sách tọa độ ghi sẵn → đường thật từ OpenRouteService → đường thẳng.
    """
    xc = KB["xe_camera"]
    if xc.get("duong"):
        return xc["duong"]
    if ORS_API_KEY:
        try:
            r = httpx.post(ORS_URL, json={"coordinates": [xc["tu"], xc["den"]]},
                           headers={"Authorization": ORS_API_KEY}, timeout=20)
            r.raise_for_status()
            toa_do = r.json()["features"][0]["geometry"]["coordinates"]
            print(f"[ORS] Hành trình xe camera: {len(toa_do)} điểm (đường thật)")
            return toa_do
        except Exception as e:
            print("[ORS] Không lấy được hành trình xe camera, dùng đường thẳng:", e)
    else:
        print("[ORS] Chưa có ORS_API_KEY — hành trình xe camera tạm dùng đường thẳng.")
    return [xc["tu"], xc["den"]]


HANH_TRINH = lay_hanh_trinh_xe_camera()


# ─────────────────────────── Nhận diện ───────────────────────────

def ma_hoa_jpeg(anh, rong_toi_da, chat_luong=70):
    """Ảnh OpenCV → chuỗi data URL JPEG để gửi qua WebSocket."""
    h, w = anh.shape[:2]
    if w > rong_toi_da:
        anh = cv2.resize(anh, (rong_toi_da, int(h * rong_toi_da / w)))
    _, buf = cv2.imencode(".jpg", anh, [cv2.IMWRITE_JPEG_QUALITY, chat_luong])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def xu_ly_khung(khung):
    """Chạy YOLO trên một khung hình. Được gọi trong luồng phụ để không chặn máy chủ."""
    r = model.predict(khung, conf=KB["nguong_tin_cay"], imgsz=640, verbose=False)[0]
    phat_hien = []
    for box in r.boxes:
        loai = r.names[int(box.cls.item())]
        if loai not in KB["lop"]:          # bỏ qua lớp không dùng (ví dụ manhole)
            continue
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
        cat = khung[max(y1, 0):max(y2, 0), max(x1, 0):max(x2, 0)]
        phat_hien.append({
            "loai": loai,
            "tin_cay": round(float(box.conf.item()), 3),
            "anh_cat": ma_hoa_jpeg(cat, 200) if cat.size else None,
        })
    return ma_hoa_jpeg(r.plot(), KB["rong_anh_gui"]), phat_hien


def gui_supabase(loai, muc_do, vi_tri):
    try:
        sb.rpc("bao_cao_su_co", {"p_loai": loai, "p_muc_do": muc_do,
                                 "p_lon": vi_tri[0], "p_lat": vi_tri[1]}).execute()
    except Exception as e:
        print("[Supabase] Lỗi:", e)


# ─────────────────────────── API ───────────────────────────

@app.get("/")
def trang_chu():
    # no-cache: trình duyệt phải hỏi lại máy chủ mỗi lần. Thiếu header này Chrome giữ
    # bản cũ trong cache, sửa giao diện xong tải lại trang vẫn thấy bản cũ.
    return FileResponse(GOC / "static" / "index.html",
                        headers={"Cache-Control": "no-cache"})


@app.get("/api/kich-ban")
def kich_ban():
    return {
        "tam_ban_do": KB["tam_ban_do"], "zoom": KB["zoom"],
        "diem_di": KB["diem_di"], "diem_den": KB["diem_den"],
        "hanh_trinh_xe_camera": HANH_TRINH,
        "hanh_lang_m": KB["hanh_lang_m"], "muc_do_doi_tuyen": KB["muc_do_doi_tuyen"],
        # Nua chieu dai khuc tuyen to do quanh moi su co (met)
        "doan_to_do_m": KB.get("doan_to_do_m", 80),
        "lop": KB["lop"],
        # Hai cờ trạng thái để giao diện báo cho người dùng biết đang thiếu gì
        "co_model": model is not None,
        "co_khoa_ors": bool(ORS_API_KEY),
        # Thông tin bản train, đọc từ model.json cạnh file model (có thể là None)
        "thong_tin_model": THONG_TIN_MODEL,
        # True khi đang chạy kich_ban.thu.json — giao diện hiện dải nhắc
        "che_do_thu": bool(KB.get("che_do_thu")),
    }


@app.post("/api/video")
async def tai_video(tep: UploadFile = File(...)):
    duoi = Path(tep.filename or "").suffix.lower()
    if duoi not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        raise HTTPException(400, "Chỉ nhận video .mp4, .mov, .avi, .mkv, .webm")
    video_id = uuid.uuid4().hex[:8]
    duong_dan = THU_MUC_UPLOAD / f"{video_id}{duoi}"
    duong_dan.write_bytes(await tep.read())

    cap = cv2.VideoCapture(str(duong_dan))
    so_khung = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    if so_khung <= 0:
        duong_dan.unlink(missing_ok=True)
        raise HTTPException(400, "Không đọc được video. Thử chuyển sang .mp4 (H.264).")
    return {"video_id": video_id, "ten": tep.filename, "so_khung": so_khung,
            "fps": round(fps, 2), "thoi_luong": round(so_khung / fps, 1)}


@app.post("/api/anh")
async def tai_anh(tep: UploadFile = File(...)):
    """Nhận diện trên MỘT ảnh chụp — nhanh hơn quay video khi muốn thử model.

    Trả về ảnh đã vẽ khung và danh sách phát hiện. Vị trí sự cố do trình duyệt
    gán (ghim tím trên bản đồ), vì ảnh chụp không có tiến độ để nội suy như video.
    """
    if model is None:
        raise HTTPException(503, f"Chưa nạp được model '{KB['model']}'. "
                                 "Đặt best.pt cạnh main.py rồi khởi động lại máy chủ.")
    duoi = Path(tep.filename or "").suffix.lower()
    if duoi not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        raise HTTPException(400, "Chỉ nhận ảnh .jpg, .jpeg, .png, .bmp, .webp")

    du_lieu = await tep.read()
    anh = cv2.imdecode(np.frombuffer(du_lieu, np.uint8), cv2.IMREAD_COLOR)
    if anh is None:
        raise HTTPException(400, "Không đọc được ảnh — tệp hỏng hoặc sai định dạng")

    # Dùng lại đúng hàm xử lý của video: cùng ngưỡng tin cậy, cùng cách lọc lớp và cắt ảnh
    anh_ve, phat_hien = await asyncio.to_thread(xu_ly_khung, anh)
    return {"ten": tep.filename, "anh": anh_ve, "phat_hien": phat_hien}


@app.websocket("/ws/nhan-dien/{video_id}")
async def nhan_dien(ws: WebSocket, video_id: str):
    await ws.accept()

    if model is None:
        await ws.send_json({"loai_tin": "loi", "noi_dung":
                            f"Chưa nạp được model '{KB['model']}'. "
                            "Đặt best.pt cạnh main.py (hoặc trong models/) rồi khởi động lại máy chủ."})
        await ws.close()
        return

    tep = next(THU_MUC_UPLOAD.glob(f"{video_id}.*"), None)
    if tep is None:
        await ws.send_json({"loai_tin": "loi", "noi_dung": "Không tìm thấy video"})
        await ws.close()
        return

    cap = cv2.VideoCapture(str(tep))
    so_khung = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    buoc = KB["buoc_khung"]
    da_bao = []                           # [(loai, vi_tri)] — chống báo trùng
    dem_lien_tiep = {loai: 0 for loai in KB["lop"]}
    so_su_co = 0
    bat_dau = time.perf_counter()
    await ws.send_json({"loai_tin": "bat_dau", "so_khung": so_khung, "fps": fps})

    try:
        chi_so = -1
        while True:
            chi_so += 1
            if chi_so % buoc:             # bỏ qua khung không cần xử lý (chỉ giải mã nhanh)
                if not cap.grab():
                    break
                continue
            ok, khung = cap.read()
            if not ok:
                break

            thoi_diem = chi_so / fps
            tien_do = chi_so / max(so_khung - 1, 1)
            vi_tri = vi_tri_theo_tien_do(HANH_TRINH, tien_do)
            anh, phat_hien = await asyncio.to_thread(xu_ly_khung, khung)

            # Chỉ xác nhận sự cố khi thấy ở N khung xử lý liên tiếp → giảm báo nhầm
            thay = {p["loai"] for p in phat_hien}
            for loai in dem_lien_tiep:
                dem_lien_tiep[loai] = dem_lien_tiep[loai] + 1 if loai in thay else 0

            await ws.send_json({
                "loai_tin": "khung", "anh": anh,
                "tien_do": round(tien_do, 4), "thoi_diem": round(thoi_diem, 2),
                "vi_tri_xe": vi_tri,
                "phat_hien": [{"loai": p["loai"], "tin_cay": p["tin_cay"]} for p in phat_hien],
            })

            for p in sorted(phat_hien, key=lambda p: -p["tin_cay"]):
                loai = p["loai"]
                if dem_lien_tiep[loai] != KB["so_khung_xac_nhan"]:
                    continue
                if any(l == loai and khoang_cach_m(v, vi_tri) < KB["ban_kinh_gop_m"]
                       for l, v in da_bao):
                    continue
                da_bao.append((loai, vi_tri))
                so_su_co += 1
                muc_do = KB["lop"][loai]["muc_do"]
                await ws.send_json({
                    "loai_tin": "su_co", "id": so_su_co, "loai": loai, "muc_do": muc_do,
                    "tin_cay": p["tin_cay"], "vi_tri": vi_tri,
                    "thoi_diem": round(thoi_diem, 2), "anh_cat": p["anh_cat"],
                })
                if sb:
                    asyncio.create_task(asyncio.to_thread(gui_supabase, loai, muc_do, vi_tri))

            # Không chạy nhanh hơn video thật, để người xem theo kịp
            if KB["phat_theo_thoi_gian_thuc"]:
                cho = thoi_diem - (time.perf_counter() - bat_dau)
                if cho > 0:
                    await asyncio.sleep(cho)

        await ws.send_json({"loai_tin": "ket_thuc", "tong_su_co": so_su_co,
                            "thoi_gian_xu_ly": round(time.perf_counter() - bat_dau, 1)})
    except WebSocketDisconnect:
        pass
    finally:
        cap.release()


# ─────────────────────────── Định tuyến ───────────────────────────

class YeuCauTuyen(BaseModel):
    diem_di: list[float]                  # [kinh độ, vĩ độ]
    diem_den: list[float]                 # [kinh độ, vĩ độ]
    vung_ne: list[list[float]] = []       # tâm các sự cố cần né, [kinh độ, vĩ độ]


def tuyen_thang(a, b):
    """Tuyến giả: đường thẳng nối hai điểm, dùng khi chưa có khóa ORS.

    Chỉ để thử giao diện — không phải đường đi thật, và không né được sự cố.
    """
    d = khoang_cach_m(a, b)
    n = max(2, int(d // 50))
    toa_do = [[a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n] for i in range(n + 1)]
    return {"toa_do": toa_do, "quang_duong_m": round(d, 1),
            "thoi_gian_s": round(d / 8.3, 1),   # ~30 km/h
            "la_tuyen_gia": True}


@app.post("/api/tuyen-duong")
async def tuyen_duong(yc: YeuCauTuyen):
    if not ORS_API_KEY:
        if KB.get("cho_phep_tuyen_gia"):
            return tuyen_thang(yc.diem_di, yc.diem_den)
        raise HTTPException(503, "Chưa đặt biến môi trường ORS_API_KEY")

    than = {"coordinates": [yc.diem_di, yc.diem_den]}
    if yc.vung_ne:
        than["options"] = {"avoid_polygons": {
            "type": "MultiPolygon",
            "coordinates": [[vung_tron(lon, lat, KB["ban_kinh_ne_m"])] for lon, lat in yc.vung_ne],
        }}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(ORS_URL, json=than, headers={"Authorization": ORS_API_KEY})
    if r.status_code != 200:
        raise HTTPException(502, f"OpenRouteService lỗi {r.status_code}: {r.text[:300]}")
    f = r.json()["features"][0]
    tom_tat = f["properties"].get("summary", {})
    return {"toa_do": f["geometry"]["coordinates"],
            "quang_duong_m": tom_tat.get("distance", 0),
            "thoi_gian_s": tom_tat.get("duration", 0),
            "la_tuyen_gia": False}
