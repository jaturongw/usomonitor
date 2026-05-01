import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import gspread
from google.auth.transport.requests import Request
from google.oauth2 import service_account


class ServiceStatus(str, Enum):
    NORMAL = "Normal"
    DOWN = "Down"


CHECK_PORTS = (80, 443, 8443)
CONNECT_TIMEOUT = 2.0


def normalize_host(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if "://" in s:
        parsed = urlparse(s)
        host = parsed.hostname
        if not host:
            return None
        return host
    return s


def service_reachable(host: str, connect_timeout: float) -> bool:
    for port in CHECK_PORTS:
        try:
            with socket.create_connection((host, port), timeout=connect_timeout):
                return True
        except OSError:
            continue
    return False


def status_for_o_cell(val_o, connect_timeout: float) -> tuple[ServiceStatus, str | None]:
    host = normalize_host(val_o)
    if not host:
        return ServiceStatus.DOWN, None
    if host == "0.0.0.0":
        return ServiceStatus.DOWN, host
    if service_reachable(host, connect_timeout):
        return ServiceStatus.NORMAL, host
    return ServiceStatus.DOWN, host


def _check_row(row: int, val_o, connect_timeout: float) -> tuple[int, ServiceStatus, str]:
    status, host = status_for_o_cell(val_o, connect_timeout)
    host_label = host if host else "(O ว่าง)"
    return row, status, host_label


def run_monitor():
    try:
        print("--- เริ่มการทำงาน ---")
        
        # 1. กำหนด Scope สำหรับ Google Sheets + ค้นหาไฟล์ชื่อใน Drive (gspread.open)
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly',
        ]

        # 2. GOOGLE_CREDS = JSON string (เช่น GitHub Actions); local ใช้ GOOGLE_APPLICATION_CREDENTIALS = path ไฟล์ .json
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path and os.path.isfile(creds_path):
                with open(creds_path, encoding='utf-8') as f:
                    creds_raw = f.read()
        if not creds_raw:
            print(
                "❌ Error: ตั้ง GOOGLE_CREDS (JSON string) หรือ "
                "GOOGLE_APPLICATION_CREDENTIALS (path ไปยัง service account .json)"
            )
            return

        try:
            creds_info = json.loads(creds_raw)
        except Exception as e:
            print(f"❌ Error: credentials ไม่ใช่ JSON ที่ถูกต้อง: {e}")
            return

        # 3. สร้าง Credentials และบังคับ Refresh เพื่อทดสอบ Token
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        
        try:
            print("⏳ กำลังขอ Access Token จาก Google...")
            creds.refresh(Request())
            print("✅ ยืนยันตัวตนสำเร็จ (Token Refreshed)")
        except Exception as auth_err:
            # จุดนี้จะบอกชัดเจนว่าทำไม Google ถึงไม่ให้เข้า
            print(f"❌ Google Auth Error: {auth_err}")
            return

        # 4. เชื่อมต่อ gspread
        client = gspread.authorize(creds)

        # 5. เปิดไฟล์ Google Sheet (ต้อง Share ให้ Email ใน JSON แล้วเท่านั้น)
        SHEET_NAME = "sites-mon"
        try:
            spreadsheet = client.open(SHEET_NAME)
            sheet = spreadsheet.get_worksheet(0)
            print(f"✅ เปิดไฟล์ '{SHEET_NAME}' สำเร็จ")
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ Error: หาไฟล์ '{SHEET_NAME}' ไม่พบ (ลืมกด Share หรือชื่อไฟล์ผิด)")
            return

        # 6. อ่าน IP/โฮสต์จากคอลัมน์ O -> เช็ค TCP 80/443/8443 แบบขนาน -> เขียน Q + R
        o_values = sheet.col_values(15)  # O = คอลัมน์ที่ 15
        header_rows = 1
        connect_timeout = float(
            os.environ.get("MONITOR_CONNECT_TIMEOUT", str(CONNECT_TIMEOUT))
        )
        max_workers = max(1, int(os.environ.get("MONITOR_CHECK_WORKERS", "8")))

        tasks = [
            (idx + 1, val_o)
            for idx, val_o in enumerate(o_values)
            if idx + 1 > header_rows
        ]
        results: list[tuple[int, ServiceStatus, str]] = []
        if tasks:
            n_workers = min(max_workers, len(tasks))
            print(f"⚙️ เช็คแบบขนาน workers={n_workers} timeout={connect_timeout}s จำนวน {len(tasks)} แถว")
            with ThreadPoolExecutor(max_workers=n_workers) as executor:
                future_map = {
                    executor.submit(_check_row, row, val_o, connect_timeout): row
                    for row, val_o in tasks
                }
                for fut in as_completed(future_map):
                    results.append(fut.result())
            results.sort(key=lambda r: r[0])
            for row, status, host_label in results:
                print(f"🔎 check แถว {row} {host_label} -> {status.value}")
            pending = [(row, status) for row, status, _ in results]
        else:
            pending = []

        tz_bkk = ZoneInfo("Asia/Bangkok")
        updated_at = datetime.now(tz_bkk).strftime("%Y-%m-%d %H:%M:%S")
        updates = []
        for row, status in pending:
            updates.append({"range": f"Q{row}", "values": [[status.value]]})
            updates.append({"range": f"R{row}", "values": [[updated_at]]})

        if updates:
            sheet.batch_update(updates, value_input_option="USER_ENTERED")
            n_rows = len(updates) // 2
            last_row = header_rows + n_rows
            print(f"✅ อัปเดต Q+R ครบ {n_rows} แถว (แถว {header_rows + 1}–{last_row}); update_at = {updated_at} (Bangkok)")

            try:
                log_sheet = spreadsheet.worksheet("updated")
            except gspread.exceptions.WorksheetNotFound:
                log_sheet = spreadsheet.add_worksheet(title="updated", rows=1000, cols=2)
            log_sheet.update(
                [[updated_at]],
                "A2",
                value_input_option="USER_ENTERED",
            )
            print("✅ บันทึกเวลารันที่ชีท 'updated'!A2 แล้ว")
        else:
            print("⚠️ ไม่มีแถวข้อมูล (คอลัมน์ O ว่างหรือมีแค่หัวตาราง)")

        print("--- จบการทำงาน ---")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}")

if __name__ == "__main__":
    run_monitor()
