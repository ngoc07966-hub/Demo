# Thư mục mẫu — chép thành thư mục phiên bản thật

Sau khi train xong:

1. Chép **cả thư mục này**, đổi tên theo dạng `v<số>-<ngày train>`, ví dụ `v1-20260925`.
2. Bỏ file `DOC_TRUOC.md` này đi.
3. Thả `best.pt` tải từ Colab vào.
4. Chép `../model.mau.json` vào, đổi tên thành `model.json`, sửa lại thông tin cho đúng.
5. Sửa `kich_ban.json` ở thư mục gốc:
   `"model": "models/v1-20260925/best.pt"`
6. Khởi động lại máy chủ.

Chi tiết xem `../README.md`.
