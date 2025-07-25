import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet_abs = client.open("AbsenceBotData").worksheet("Absences")
sheet_lunch = client.open("AbsenceBotData").worksheet("Lunch")

def log_absence(user, date_str, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_abs.append_row([now, user, date_str, reason])

def log_lunch_start(user, start_time, end_time):
    sheet_lunch.append_row([start_time.strftime("%Y-%m-%d %H:%M:%S"), user,
                            end_time.strftime("%Y-%m-%d %H:%M:%S"), "", ""])

def log_lunch_return(user, return_time, is_late):
    records = sheet_lunch.get_all_records()
    for i in reversed(range(len(records))):
        if records[i]["Сотрудник"] == user and records[i]["Факт возврата"] == "":
            row_index = i + 2
            sheet_lunch.update_cell(row_index, 4, return_time.strftime("%Y-%m-%d %H:%M:%S"))
            sheet_lunch.update_cell(row_index, 5, "Да" if is_late else "Нет")
            break

def check_late_return(start_time, return_time):
    return return_time > start_time + timedelta(minutes=45)