import logging
from datetime import datetime

import gspread
from gspread import SpreadsheetNotFound

formatted_date = datetime(datetime.today().year, datetime.today().month, 1)
gc = gspread.service_account(filename="./gsheet_config.json")


def open_google_sheets():
    """Open Google Sheets that we will use to insert data in """
    spreadsheet_name = formatted_date.today().strftime("%Y.%m")
    try:
        return gc.open(spreadsheet_name)
    except SpreadsheetNotFound:
        logging.warning("Spreasheet with name: %s not found", spreadsheet_name)


def get_worksheet_and_categories_lists():
    """ Return list of worksheets and list of categories """
    sh = open_google_sheets()
    worksheet_list = sh.worksheets()
    worksheet_list = worksheet_list[:len(worksheet_list) - 2]
    category_list = [f"{worksheet_list.index(i) + 1}. {i.title}" for i in worksheet_list]

    return worksheet_list, category_list


if __name__ == "__main__":
    # sh = open_google_sheets()
    # w = sh.worksheet("Rent")
    # print(w.title)
    # cols_count = w.col_count
    # print  (w.col_values(cols_count)[:2])

    get_worksheet_and_categories_lists()
