"""Main File where WebServer is configured"""
import os
import logging
from datetime import datetime

import requests
import gspread
import telebot
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

logger = logging.getLogger("main")

load_dotenv()  # will dissapear after dockerzitaion

""""
$ export TOKEN=<bot_token>
$ export CHAT_ID=<chat_id>
"""

TG_TOKEN = os.getenv("TG_TOKEN", None)
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT", None)
USER_ID = int(os.getenv("USER_ID", None))

URL = f"https://api.telegram.org/bot{TG_TOKEN}/"

datem = datetime(datetime.today().year, datetime.today().month, 1)

gc = gspread.service_account(filename=SERVICE_ACCOUNT)
bot = telebot.TeleBot(TG_TOKEN)

app = FastAPI()


@app.get("/health")
def health_check():
    """Method that is checking if server is running and return Telegram User Info"""
    req = requests.get(f"{URL}getMe")
    return {"Message": req.json(), "status": 200}


@app.route("/set_webhook", methods=["GET", "POST"])
async def set_webhook(request: Request):
    if request.headers.get("content-type") == "application/json":
        json_string = await request.json()
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        result = Response(content="Executing")
    else:
        result = Response(content="Error Occurred")
    return result


def next_available_row(worksheet):
    """
    This function accepts worksheet as an argument and returns empty row number as result.
    Function also adds 5 rows if last row is not empty.
    Worksheet should be whole element from worksheet list returned from Spreadsheet.
    """
    i = worksheet.col_count - 1  # "-1" to skip last column in column, as it contains calculations
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
    last_row = refactor_table[-1]
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


class FinanceTrackBot:
    def __init__(self):
        chat_id = None


# TODO do a decorator to check user ID


@bot.message_handler(commands=["start", "Start", "help", "Help"])
def handle_start_help(message):
    """
    Shows start menu with all supported commands.
    """
    if message.from_user.id == USER_ID:
        # noinspection SpellCheckingInspection
        bot.send_message(message.chat.id, "All available commands:\n"
                                          "/start or /help shows help menu\n\n"
                                          "/CurrentMonthBalance or /CMB\n shows current month balance\n\n"
                                          "/DefinedMonthBalance or /DMB\n shows defined month balance\n\n\n"
                                          "/CurrentMonthExpenseByCategory\n retrieves expenses for current month for "
                                          "every category\n\n"
                                          "/ExactMonthExpenseByCategory\n retrieves expenses for defined month for "
                                          "every "
                                          "category\n\n\n"
                                          "/AddExpenseToCurrentMonth or /AECM\n adds expense to current month\n\n"
                                          "/AddExpenseToDefinedMonth or /AEDM\n adds expense to defined month\n\n\n"
                                          "/FormatDefinedFile or /FDF\n restores correct formating for whole document"
                                          " defined by date, takes up to 5 minutes, do not use frequently\n"
                         )
    else:
        bot.send_message(message.chat.id, "Access denied!!!\nPlease ensure you have right to use this bot!")


@bot.message_handler(commands=["AddExpenseToCurrentMonth", "AECM", "aecm"])
def add_expense_to_current_month(message):
    """
    Add expense to current month

    :param message:
    """
    if message.from_user.id == USER_ID:
        sh = gc.open(datem.today().strftime("%Y.%m"))
        worksheet_list = sh.worksheets()
        worksheet_list = worksheet_list[:len(worksheet_list) - 2]
        category_list = [f"{worksheet_list.index(i) + 1}. {i.title}" for i in worksheet_list]
        bot.send_message(message.chat.id, "\n".join([_ for _ in category_list]))
        msg = bot.reply_to(message, 'Please choose the expense category number from message above: ')
        bot.register_next_step_handler(msg, add_current_month_expense_input_category, worksheet_list)
    else:
        bot.send_message(message.chat.id, "Access denied!!!\nPlease ensure you have right to use this bot!")


def add_current_month_expense_input_category(message, worksheet_list):
    """

    :param message:
    :param worksheet_list:
    """
    try:
        category_num = int(message.text) - 1
    except ValueError:
        bot.reply_to(message, "Incorrect Category!")

    try:
        if worksheet_list[category_num] in worksheet_list and int(message.text) > 0:
            bot.send_message(message.chat.id, 'You have chosen: ' + str(message.text) + ") " +
                             (worksheet_list[category_num]).title)
            msg = bot.reply_to(message, 'Please enter tag and price as example "Bread: 50": ')
            bot.register_next_step_handler(msg, add_current_month_expense_input_string, category_num)
        else:
            bot.send_message(message.chat.id, 'Category with number: ' + str(message.text) + ' '
                                                                                             'not found! Please retry')
            msg = bot.reply_to(message, 'Please choose the expense category number from message above: ')
            bot.register_next_step_handler(msg, add_current_month_expense_input_category, worksheet_list)
    except Exception as e:
        bot.reply_to(message, 'ERROR!\nCategory ' + str(message.text) + ' not found!\nTry once more!')
        msg = bot.reply_to(message, 'Please choose the expense category number from message above: ')
        bot.register_next_step_handler(msg, add_current_month_expense_input_category, worksheet_list)
        logger.error(str(e))


def add_current_month_expense_input_string(message, category_num):
    """
    This function is 3/3 step process of adding expense to current month
    expense from input_list[0] as expense
    price from input_list[1] as price
    and category number (worksheet) from message.text
    And finally format cells as expected and fills up information to empty row
    """
    input_list = message.text.split(':')

    if len(input_list) == 2:
        sh = gc.open(datem.today().strftime("%Y.%m"))
        today_date = datem.today().strftime("%d.%m.%Y")
        worksheet_list = sh.worksheets()
        worksheet = worksheet_list[category_num]
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
        worksheet.update('A' + str(empty_string), input_list[0])
        worksheet.update('B' + str(empty_string), today_date, value_input_option='USER_ENTERED')
        worksheet.update('C' + str(empty_string), int(input_list[1]))
        read_row_str = (', '.join(map(str, worksheet.get(
            'A' + str(empty_string) + ":" + 'C' + str(empty_string))
                                      ))).strip('[]')
        bot.send_message(
            message.chat.id, read_row_str + ""
                                            " has been added to "
                                            "" + worksheet.title + ""
                                                                   " worksheet into " + datem.today().strftime(
                "%Y.%m") + " file.")
    else:
        bot.send_message(message.chat.id,
                         "You have entered *** " + message.text + " *** - wrong input format (Expense:price) or not 2 "
                                                                  "parameters in the input")
        sh = gc.open(datem.today().strftime("%Y.%m") + " Family budget")
        worksheet_list = sh.worksheets()
        msg = bot.reply_to(message, "Please enter the expense for "
                                    "" + str(datem.today().strftime("%Y.%m")) + ""
                                                                                " and " + str(
            worksheet_list[category_num].title) + ""
                                                  " category in format expense:price")
        bot.register_next_step_handler(msg, add_current_month_expense_input_string, category_num)


@bot.message_handler(commands=["CurrentMonthBalance", "CMB", "cmb"])
def current_month_balance(message):
    """
    Method that returns 3 different data to User: income, expense and balance
    :param message:
    :return: Current income, expense and balance
    """

    if message.from_user.id == USER_ID:
        sh = gc.open(datem.today().strftime("%Y.%m"))
        worksheet = sh.worksheet("Balance")
        bot.send_message(message.chat.id, "Current month income is: " + worksheet.acell('B15').value)
        bot.send_message(message.chat.id, "Current month expenses are: " + worksheet.acell('D15').value)
        bot.send_message(message.chat.id, "Current month balance is: " + worksheet.acell('F1').value)
    else:
        bot.send_message(message.chat.id, "Access denied!!!\nPlease ensure you have right to use this bot!")




