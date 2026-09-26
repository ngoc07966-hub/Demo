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
import sys
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
import torch  # noqa: F401  phải nạp TRƯỚC ultralytics: ultralytics đặt OMP_NUM_THREADS=1, torch nạp sau sẽ chỉ chạy 1 luồng CPU
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


LOAI_MODEL = KB.get("loai_model", "yolo")   # "yolo" (mặc định) hoặc "road_hazard"


def nap_model_yolo():
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


def nap_model_road_hazard():
    """→ (adapter dict, thông tin bản train). Nạp checkpoint của dự án road_hazard
    (kiến trúc CNN + FPN + Detection/Seg/Env + Decision Layer, xem road_hazard/AGENTS.md).

    Checkpoint hiện có (rdd_det_r18_aug960) CHỈ train phần detection (pothole, crack) trên
    RDD2022 — chưa có segmentation/environment/flood, và chậm hơn YOLO nhiều trên CPU. Xem
    TOM_TAT_CHO_CHAT_MOI.md mục 2.3 trước khi coi đây là model chính thức của báo cáo.
    """
    rh = KB.get("road_hazard", {})
    ma_nguon = (GOC / rh.get("duong_dan_code", "../../road_hazard")).resolve()
    duong_dan = (GOC / rh.get("checkpoint", "../../road_hazard/runs/rdd_det_r18_aug960/best.pt")).resolve()
    if not ma_nguon.is_dir():
        print(f"[Model] road_hazard ✗ Không thấy thư mục mã nguồn: {ma_nguon}")
        return None, None
    if not duong_dan.exists():
        print(f"[Model] road_hazard ✗ Không thấy checkpoint: {duong_dan}")
        return None, None
    try:
        if str(ma_nguon) not in sys.path:
            sys.path.insert(0, str(ma_nguon))
        import torch
        from config import DET_CLASSES, ModelConfig
        from model import RoadHazardNet, StreamingRunner
        from reproducibility import resolve_device

        device = resolve_device("auto")
        ck = torch.load(str(duong_dan), map_location=device, weights_only=False)
        cfg = ModelConfig(**{**ck["cfg"], "pretrained": False})
        net = RoadHazardNet(cfg).to(device)
        net.load_state_dict(ck["model"])
        net.eval()
        tasks = tuple(ck.get("tasks") or ("det",))
        print(f"[Model] road_hazard: đã nạp {duong_dan}")
        print(f"[Model] road_hazard: task đã train = {tasks}, img_size = {cfg.img_size}, thiết bị = {device}")
        if "seg" not in tasks:
            print("[Model] road_hazard ⚠ chưa train segmentation -> KHÔNG lọc theo mặt đường")
        if "env" not in tasks:
            print("[Model] road_hazard ⚠ chưa train environment -> KHÔNG có nhãn thời tiết")
        # Đầu ra của lớp chưa từng có nhãn khi train (vd flood khi chỉ train RDD2022) là số rác, có thể
        # lên 0.9 → chỉ tin lớp có AP đo được trên tập val. Ghi đè bằng road_hazard.lop_da_train nếu cần.
        ap = (ck.get("metrics") or {}).get("det_AP50") or {}
        lop_da_train = rh.get("lop_da_train") or [c for c, v in ap.items() if v is not None]
        print(f"[Model] road_hazard: lớp đã train (có AP trên tập val) = {lop_da_train}")
        if not lop_da_train:
            print("[Model] road_hazard ⚠ checkpoint không ghi lớp nào đã train — khai road_hazard.lop_da_train")
        bo = [c for c in DET_CLASSES if c not in lop_da_train]
        if bo:
            print(f"[Model] road_hazard: bỏ đầu ra các lớp chưa train: {bo}")
        thieu = [l for l in KB["lop"] if l not in lop_da_train]
        if thieu:
            print(f"[Model] road_hazard ⚠ Lớp khai trong kich_ban.json nhưng model CHƯA train: {thieu}")

        # Nhánh segmentation chưa train thì không tính, đỡ ~50 ms/khung trên CPU
        adapter = {"runner": StreamingRunner(net, with_seg="seg" in tasks), "device": device,
                   "tasks": tasks, "img_size": cfg.img_size, "lop": set(lop_da_train)}
        tt = {"phien_ban": f"road_hazard ({duong_dan.parent.name}, {cfg.backbone}, {cfg.img_size}px)",
              "checkpoint": str(duong_dan), "tasks": list(tasks),
              "dataset": f"RDD2022 — lớp đã train: {', '.join(lop_da_train) or 'không rõ'}"}
        return adapter, tt
    except Exception as e:
        print(f"[Model] road_hazard ✗ Không nạp được '{duong_dan}': {e}")
        return None, None


CAC_MODEL = {
    "yolo": {"ten": "YOLO11n (model chính)", "nap": nap_model_yolo},
    "road_hazard": {"ten": "road_hazard (thử nghiệm)", "nap": nap_model_road_hazard},
}
DA_NAP = {}                               # loại → (model, thông tin); nạp lần đầu khi cần


def lay_model(loai):
    """Nạp model nếu chưa có (hoặc lần trước nạp lỗi) rồi giữ lại để đổi qua lại cho nhanh."""
    if DA_NAP.get(loai, (None, None))[0] is None:
        DA_NAP[loai] = CAC_MODEL[loai]["nap"]()
    return DA_NAP[loai]


if LOAI_MODEL not in CAC_MODEL:
    print(f"[Model] ⚠ loai_model '{LOAI_MODEL}' không hợp lệ (chỉ nhận {list(CAC_MODEL)}) — dùng yolo")
    LOAI_MODEL = "yolo"
model, THONG_TIN_MODEL = lay_model(LOAI_MODEL)
KHOA_DOI_MODEL = asyncio.Lock()


def ten_model_hien_thi():
    if LOAI_MODEL == "yolo":
        return KB["model"]
    return KB.get("road_hazard", {}).get("checkpoint", "road_hazard")


app = FastAPI(title="Demo nhận diện sự cố giao thông")
app.mount("/static", StaticFiles(directory=GOC / "static"), name="static")

# Supabase — bật/tắt trong kich_ban.json, nhưng URL/khóa lấy từ .env (không đưa khóa lên Git)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip() or KB.get("supabase", {}).get("url", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip() or KB.get("supabase", {}).get("anon_key", "")

sb = None
if KB.get("supabase", {}).get("bat"):
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("[Supabase] Đã kết nối — sự cố nhận diện được sẽ gửi lên bảng su_co.")
    else:
        print("[Supabase] ⚠ Đã bật trong kich_ban.json nhưng thiếu SUPABASE_URL / SUPABASE_ANON_KEY trong .env")


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
        # max(1, …): hộp rất dẹt (vd 250×1 px) làm chiều cao tính ra 0 → cv2.resize báo lỗi, ngắt cả video
        anh = cv2.resize(anh, (rong_toi_da, max(1, int(h * rong_toi_da / w))))
    _, buf = cv2.imencode(".jpg", anh, [cv2.IMWRITE_JPEG_QUALITY, chat_luong])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def hop_ti_le(x1, y1, x2, y2, w, h):
    """Toạ độ hộp theo tỉ lệ 0..1 của khung — trình duyệt tự vẽ đè lên video ở mọi kích thước."""
    return [round(min(max(v, 0.0), 1.0), 4) for v in (x1 / w, y1 / h, x2 / w, y2 / h)]


def xu_ly_khung_yolo(khung, m, ve_anh=True):
    r = m.predict(khung, conf=KB["nguong_tin_cay"], imgsz=640, verbose=False)[0]
    h, w = khung.shape[:2]
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
            "hop": hop_ti_le(x1, y1, x2, y2, w, h),
            "anh_cat": ma_hoa_jpeg(cat, 200) if cat.size else None,
        })
    return (ma_hoa_jpeg(r.plot(), KB["rong_anh_gui"]) if ve_anh else None), phat_hien


def xu_ly_khung_road_hazard(khung, m, ve_anh=True):
    """Chạy model road_hazard (chỉ phần detection) trên một khung hình.

    Không dùng Decision Layer / tracker riêng của road_hazard ở đây — việc xác nhận qua
    nhiều khung liên tiếp đã do main.py tự làm (biến dem_lien_tiep), giống hệt nhánh YOLO,
    để hai model so sánh được công bằng với cùng một luật xác nhận.
    """
    import torch
    from decision import decode_detections
    from data.transforms import letterbox, boxes_from_letterbox

    S = m["img_size"]
    lb, params = letterbox(khung, S)
    rgb = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB)
    x = torch.from_numpy(rgb).permute(2, 0, 1)[None].float().div(255).to(m["device"])
    with torch.no_grad():
        out = m["runner"].step(x)
    # Điểm heatmap CenterNet thấp hơn điểm YOLO nên cần ngưỡng riêng (mặc định 0.35 như DecisionConfig)
    dets = decode_detections(out, KB.get("road_hazard", {}).get("nguong_tin_cay", 0.35))[0]

    anh_ve = khung.copy() if ve_anh else None
    phat_hien = []
    h, w = khung.shape[:2]
    for d in dets:
        loai = d["cls"]
        if loai not in KB["lop"] or loai not in m["lop"]:
            continue
        x1, y1, x2, y2 = boxes_from_letterbox([d["bbox"]], params)[0].tolist()
        x1, y1 = max(int(x1), 0), max(int(y1), 0)
        x2, y2 = min(int(x2), w), min(int(y2), h)
        if ve_anh:
            cv2.rectangle(anh_ve, (x1, y1), (x2, y2), (0, 165, 255), 2)
            cv2.putText(anh_ve, f"{loai} {d['score']:.2f}", (x1, max(y1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        cat = khung[y1:y2, x1:x2]
        phat_hien.append({
            "loai": loai,
            "tin_cay": round(float(d["score"]), 3),
            "hop": hop_ti_le(x1, y1, x2, y2, w, h),
            "anh_cat": ma_hoa_jpeg(cat, 200) if cat.size else None,
        })
    return (ma_hoa_jpeg(anh_ve, KB["rong_anh_gui"]) if ve_anh else None), phat_hien


def xu_ly_khung(khung, loai, m, ve_anh=True):
    """Chạy model trên một khung hình. Được gọi trong luồng phụ để không chặn máy chủ.

    ve_anh=False: không vẽ hộp, không nén cả khung (video — trình duyệt tự vẽ đè lên video gốc).
    """
    if loai == "road_hazard":
        return xu_ly_khung_road_hazard(khung, m, ve_anh)
    return xu_ly_khung_yolo(khung, m, ve_anh)


# ─────────────── Kho sự cố dùng chung (trang "Xe đi sau" đọc lại) ───────────────
# Giữ trong bộ nhớ máy chủ: khởi động lại là mất. Mỗi lần chạy video mới là một
# "phiên" mới — xe sau thấy phiên đổi thì tải lại toàn bộ danh sách.

KHO_SU_CO = {"phien": uuid.uuid4().hex[:8], "ds": []}


def phien_moi():
    KHO_SU_CO["phien"] = uuid.uuid4().hex[:8]
    KHO_SU_CO["ds"] = []


def luu_su_co(sc):
    """Ghi một sự cố vào kho chung, trả về bản đã lưu (có mã và giờ ghi nhận)."""
    ban = {**sc, "ma": len(KHO_SU_CO["ds"]) + 1, "luc": time.time()}
    KHO_SU_CO["ds"].append(ban)
    return ban


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


@app.get("/xe-sau")
def trang_xe_sau():
    return FileResponse(GOC / "static" / "xe_sau.html")


@app.get("/api/su-co")
def ds_su_co(phien: str = "", tu: int = 0):
    """Sự cố đã ghi nhận. Cùng phiên thì chỉ trả phần mới (từ vị trí `tu`), khác phiên thì trả hết."""
    if phien != KHO_SU_CO["phien"]:
        tu = 0
    return {"phien": KHO_SU_CO["phien"], "tu": tu, "ds": KHO_SU_CO["ds"][tu:]}


class SuCoAnh(BaseModel):
    loai: str
    tin_cay: float
    vi_tri: list[float]                   # [kinh độ, vĩ độ]
    anh_cat: str | None = None
    ten_tep: str | None = None


@app.post("/api/su-co")
def them_su_co_anh(sc: SuCoAnh):
    """Sự cố tìm thấy trong ảnh chụp (vị trí do trình duyệt gán) — ghi vào kho chung như sự cố từ video."""
    if sc.loai not in KB["lop"]:
        raise HTTPException(400, f"Loại không hợp lệ: {sc.loai}")
    return luu_su_co({**sc.model_dump(), "muc_do": KB["lop"][sc.loai]["muc_do"],
                      "thoi_diem": None, "nguon": "anh"})


@app.delete("/api/su-co")
def xoa_su_co():
    """Xóa toàn bộ kho sự cố dùng chung (để kiểm tra lại từ đầu). Không xóa dữ liệu đã gửi lên Supabase."""
    so = len(KHO_SU_CO["ds"])
    phien_moi()
    return {"phien": KHO_SU_CO["phien"], "da_xoa": so}


@app.get("/api/kich-ban")
def kich_ban():
    return {
        "tam_ban_do": KB["tam_ban_do"], "zoom": KB["zoom"],
        "diem_di": KB["diem_di"], "diem_den": KB["diem_den"],
        "hanh_trinh_xe_camera": HANH_TRINH,
        "hanh_lang_m": KB["hanh_lang_m"], "muc_do_doi_tuyen": KB["muc_do_doi_tuyen"],
        "doan_canh_bao_m": KB.get("doan_canh_bao_m", 50),
        "ban_kinh_ne_m": KB["ban_kinh_ne_m"],
        "canh_bao_truoc_m": KB.get("canh_bao_truoc_m", 300),
        "so_su_co_goi_y_doi_tuyen": KB.get("so_su_co_goi_y_doi_tuyen", 3),
        "lop": KB["lop"],
        # Hai cờ trạng thái để giao diện báo cho người dùng biết đang thiếu gì
        "co_model": model is not None,
        "co_khoa_ors": bool(ORS_API_KEY),
        # Thông tin bản train, đọc từ model.json cạnh file model (có thể là None)
        "thong_tin_model": THONG_TIN_MODEL,
        "loai_model": LOAI_MODEL,
        "cac_model": {k: v["ten"] for k, v in CAC_MODEL.items()},
        # True khi đang chạy kich_ban.thu.json — giao diện hiện dải nhắc
        "che_do_thu": bool(KB.get("che_do_thu")),
    }


class YeuCauDoiModel(BaseModel):
    loai: str


@app.post("/api/model")
async def doi_model(yc: YeuCauDoiModel):
    """Đổi model đang dùng mà không cần khởi động lại máy chủ.

    Video đang chạy dở vẫn giữ model lúc bắt đầu; model mới áp dụng cho lần nhận diện sau.
    """
    global LOAI_MODEL, model, THONG_TIN_MODEL
    if yc.loai not in CAC_MODEL:
        raise HTTPException(400, f"Model không hợp lệ. Chỉ nhận: {list(CAC_MODEL)}")
    async with KHOA_DOI_MODEL:
        m, tt = await asyncio.to_thread(lay_model, yc.loai)
        if m is None:
            raise HTTPException(503, f"Không nạp được model {CAC_MODEL[yc.loai]['ten']} — xem log máy chủ.")
        LOAI_MODEL, model, THONG_TIN_MODEL = yc.loai, m, tt
    print(f"[Model] Đã chuyển sang: {CAC_MODEL[yc.loai]['ten']}")
    return {"loai_model": LOAI_MODEL, "thong_tin_model": THONG_TIN_MODEL}


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
    loai, m = LOAI_MODEL, model
    if m is None:
        raise HTTPException(503, f"Chưa nạp được model '{ten_model_hien_thi()}'. "
                                 "Kiểm tra đường dẫn model trong kich_ban.json rồi khởi động lại máy chủ.")
    duoi = Path(tep.filename or "").suffix.lower()
    if duoi not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        raise HTTPException(400, "Chỉ nhận ảnh .jpg, .jpeg, .png, .bmp, .webp")

    du_lieu = await tep.read()
    anh = cv2.imdecode(np.frombuffer(du_lieu, np.uint8), cv2.IMREAD_COLOR)
    if anh is None:
        raise HTTPException(400, "Không đọc được ảnh — tệp hỏng hoặc sai định dạng")

    # Dùng lại đúng hàm xử lý của video: cùng ngưỡng tin cậy, cùng cách lọc lớp và cắt ảnh
    anh_ve, phat_hien = await asyncio.to_thread(xu_ly_khung, anh, loai, m)
    return {"ten": tep.filename, "anh": anh_ve, "phat_hien": phat_hien}


@app.websocket("/ws/nhan-dien/{video_id}")
async def nhan_dien(ws: WebSocket, video_id: str):
    await ws.accept()

    loai_model, m = LOAI_MODEL, model     # giữ cố định suốt video, dù có đổi model giữa chừng
    if m is None:
        await ws.send_json({"loai_tin": "loi", "noi_dung":
                            f"Chưa nạp được model '{ten_model_hien_thi()}'. "
                            "Kiểm tra đường dẫn model trong kich_ban.json rồi khởi động lại máy chủ."})
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
    if loai_model == "road_hazard":       # model chậm hơn nhiều → bỏ qua nhiều khung hơn để theo kịp video
        buoc = KB.get("road_hazard", {}).get("buoc_khung", buoc)
    da_bao = []                           # [(loai, vi_tri)] — chống báo trùng
    phien_moi()                           # chạy video mới → xe sau bắt đầu lại từ danh sách trống
    dem_lien_tiep = {loai: 0 for loai in KB["lop"]}
    so_su_co = so_bo_qua = 0
    bat_dau = time.perf_counter()
    await ws.send_json({"loai_tin": "bat_dau", "so_khung": so_khung, "fps": fps, "buoc": buoc})

    try:
        chi_so = -1
        while True:
            chi_so += 1
            xu_ly = chi_so % buoc == 0
            # Trình duyệt phát video gốc theo thời gian thực: máy chủ tụt lại quá một bước thì bỏ khung để bắt kịp,
            # nếu không hộp vẽ ra sẽ trễ dần so với hình
            if xu_ly and KB["phat_theo_thoi_gian_thuc"] \
                    and (time.perf_counter() - bat_dau) - chi_so / fps > buoc / fps:
                xu_ly = False
                so_bo_qua += 1
            if not xu_ly:                 # bỏ qua khung không cần xử lý (chỉ giải mã nhanh)
                if not cap.grab():
                    break
                continue
            ok, khung = cap.read()
            if not ok:
                break

            thoi_diem = chi_so / fps
            tien_do = chi_so / max(so_khung - 1, 1)
            vi_tri = vi_tri_theo_tien_do(HANH_TRINH, tien_do)
            _, phat_hien = await asyncio.to_thread(xu_ly_khung, khung, loai_model, m, False)

            # Chỉ xác nhận sự cố khi thấy ở N khung xử lý liên tiếp → giảm báo nhầm
            thay = {p["loai"] for p in phat_hien}
            for loai in dem_lien_tiep:
                dem_lien_tiep[loai] = dem_lien_tiep[loai] + 1 if loai in thay else 0

            # Chỉ gửi toạ độ hộp (vài trăm byte), trình duyệt tự vẽ đè lên video gốc đang phát
            await ws.send_json({
                "loai_tin": "khung",
                "tien_do": round(tien_do, 4), "thoi_diem": round(thoi_diem, 3),
                "vi_tri_xe": vi_tri,
                "phat_hien": [{"loai": p["loai"], "tin_cay": p["tin_cay"], "hop": p["hop"]} for p in phat_hien],
            })

            for p in sorted(phat_hien, key=lambda p: -p["tin_cay"]):
                loai = p["loai"]
                if dem_lien_tiep[loai] < KB["so_khung_xac_nhan"]:
                    continue
                if any(l == loai and khoang_cach_m(v, vi_tri) < KB["ban_kinh_gop_m"]
                       for l, v in da_bao):
                    continue
                da_bao.append((loai, vi_tri))
                so_su_co += 1
                muc_do = KB["lop"][loai]["muc_do"]
                sc = {"id": so_su_co, "loai": loai, "muc_do": muc_do,
                      "tin_cay": p["tin_cay"], "vi_tri": vi_tri,
                      "thoi_diem": round(thoi_diem, 2), "anh_cat": p["anh_cat"], "nguon": "video"}
                luu_su_co(sc)
                await ws.send_json({"loai_tin": "su_co", **sc})
                if sb:
                    asyncio.create_task(asyncio.to_thread(gui_supabase, loai, muc_do, vi_tri))

            # Không chạy nhanh hơn video thật, để người xem theo kịp
            if KB["phat_theo_thoi_gian_thuc"]:
                cho = thoi_diem - (time.perf_counter() - bat_dau)
                if cho > 0:
                    await asyncio.sleep(cho)

        await ws.send_json({"loai_tin": "ket_thuc", "tong_su_co": so_su_co, "so_khung_bo_qua": so_bo_qua,
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
