"""Module that will contain all important methods, configs """
import logging
import os
from datetime import datetime

import gspread
import telebot
from gspread import SpreadsheetNotFound

""""
$ export TOKEN=<bot_token>
$ export CHAT_ID=<chat_id>
"""

TG_TOKEN = os.environ.get("TG_TOKEN")
SERVICE_ACCOUNT = os.environ.get("SERVICE_ACCOUNT")
USERS_ID = os.environ.get("USER_ID")

URL = f"https://api.telegram.org/bot{TG_TOKEN}/"

gc = gspread.service_account(filename=SERVICE_ACCOUNT)
bot = telebot.TeleBot(TG_TOKEN)

formatted_date = datetime(datetime.today().year, datetime.today().month, 1)


def check_user_authorization_telegram(func):
    """Decorator that is checking if user that is accessing telegram bot is authorized or not"""

    def wrapper(*args, **kwargs):
        if not USERS_ID and kwargs.get("message").from_user.id in USERS_ID.split(":"):
            func(*args, *kwargs)
        else:
            bot.send_message(kwargs.get("message").chat.id,
                             "Access denied!!!\nPlease ensure you have right to use this bot!")

    return wrapper


def open_google_sheets():
    """Open Google Sheets that we will use to insert data in """
    spreadsheet_name = formatted_date.today().strftime("%Y.%m")
    try:
        return gc.open(spreadsheet_name)
    except SpreadsheetNotFound:
        logging.warning("Spreasheet with name: %s not found", spreadsheet_name)


def next_available_row(worksheet):
    """
    This function accepts worksheet as an argument and returns empty row number as result.
    Function also adds 5 rows if last row is not empty.
    Worksheet should be whole element from worksheet list returned from Spreadsheet.
    """
    i = worksheet.col_count - 1  # "-1" to skip last column in table, as it contains calculations
    result_list = []
    while i > 0:
        result = len(list(filter(None, worksheet.col_values(i))))
        result_list.append(result)
        i = i - 1
    result_list.sort()
    empty_row = result_list[-1]
    refactor_table = worksheet.get_all_records()
    # delete from table date last column that contains calculations for all the sums
    [i.pop(list(i)[-1]) for i in refactor_table]
    last_row = [] if not refactor_table else refactor_table[-1]
    if last_row:
        worksheet.resize(int(empty_row) + 5)
        try:
            worksheet.row_values(empty_row)
            empty_row = empty_row + 1
        except Exception:
            return empty_row
    else:
        try:
            worksheet.row_values(empty_row)
            empty_row = empty_row + 1
        except Exception:
            return empty_row
    return empty_row


def add_input_data_to_google_sheet(input_data, worksheet):
    """Method checks if input data exists and add formatted data to G Sheet"""
    today_date = formatted_date.today().strftime("%d.%m.%Y")
    empty_string = next_available_row(worksheet)
    worksheet.format('A' + str(empty_string), {"horizontalAlignment": "LEFT",
                                               "textFormat": {
                                                   "fontSize": 12
                                               }
                                               })
    worksheet.format('B' + str(empty_string), {"horizontalAlignment": "CENTER",
                                               "numberFormat": {
                                                   "type": "DATE",
                                                   "pattern": "dd.mm.yyyy"},
                                               "textFormat": {
                                                   "fontSize": 12
                                               }
                                               })
    worksheet.format('C' + str(empty_string), {"horizontalAlignment": "RIGHT",
                                               "numberFormat": {
                                                   "type": "CURRENCY",
                                                   "pattern": "€ #,##0.00"},
                                               "textFormat": {
                                                   "fontSize": 12
                                               }
                                               })
    worksheet.update('A' + str(empty_string), input_data[0])
    worksheet.update('B' + str(empty_string), today_date, value_input_option='USER_ENTERED')

    try:
        sum_number = int(input_data[1])
    except ValueError:
        sum_number = float(input_data[1])

    worksheet.update('C' + str(empty_string), sum_number)
    return ', '.join(map(str, worksheet.get('A' + str(empty_string) + ":" + 'C' + str(empty_string)))).strip('[]')
