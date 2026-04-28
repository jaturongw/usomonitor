import gspread
import os
import json
from google.oauth2 import service_account

def test_simple_transfer():
    try:
        # 1. ตั้งค่า Scopes ให้ถูกต้อง (ต้องใช้ 2 ตัวนี้)
        scope = [
            'https://googleapis.com',
            'https://googleapis.com'
        ]

        # 2. โหลด Credentials จาก GitHub Secrets
        creds_raw = os.environ.get('GOOGLE_CREDS')
        if not creds_raw:
            print("❌ ไม่พบ GOOGLE_CREDS ใน Environment")
            return

        creds_info = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)

        # 3. เปิดไฟล์และทำงานกับ Cell
        SHEET_NAME = "sites-mon"
        sheet = client.open(SHEET_NAME).get_worksheet(0)

        # อ่านค่าจาก O2
        val = sheet.acell('O2').value
        print(f"📖 อ่านค่าจาก O2 ได้: {val}")

        # เขียนค่าลงใน Q2
        if val:
            sheet.update_acell('Q2', f"Test: {val}")
            print(f"✅ เขียนลง Q2 สำเร็จ!")
        else:
            print("⚠️ ช่อง O2 ว่างเปล่า ไม่ได้เขียนอะไรลงไป")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    test_simple_transfer()

if __name__ == "__main__":
    run_monitor()
