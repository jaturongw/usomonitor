import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import subprocess
import json
from datetime import datetime

try:
    # Setup Credentials
    scope = ["https://google.com", "https://googleapis.com"]
    creds_json = json.loads(os.environ['GOOGLE_CREDS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)

    # *** IMPORTANT: Change this to your EXACT Google Sheet filename ***
    SHEET_NAME = "sites-mon" 
    sheet = client.open(SHEET_NAME).get_worksheet(0)

    # Get IP list from Column O (15)
    ip_list = sheet.col_values(15)[1:40]

    results = []
    for ip in ip_list:
        ip = ip.strip()
        if ip and ip != "0.0.0.0":
            # Ping command (Ubuntu runner uses -c for count and -W for timeout)
            process = subprocess.run(['ping', '-c', '1', '-W', '2', ip], stdout=subprocess.DEVNULL)
            results.append(["Normal"] if process.returncode == 0 else ["Down"])
        else:
            results.append(["Down"])

    # Update Column Q (17)
    if results:
        sheet.update(f"Q2:Q{len(results)+1}", results)

    # Update Timestamp in R2
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sheet.update_acell("R2", f"Update: {now}")
    print(f"Success: Updated at {now}")

except Exception as e:
    print(f"Error occurred: {e}")
    exit(1) # This tells GitHub that the process failed
