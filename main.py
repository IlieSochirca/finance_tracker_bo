"""Main File where WebServer is configured"""
import logging
import requests
import telebot
from fastapi import FastAPI, Request, Response

from utility import URL, bot, check_user_authorization_telegram, \
    open_google_sheets, formatted_date, add_input_data_to_google_sheet, get_worksheet_list_and_register_handler, \
    validate_input_category

logger = logging.getLogger("main")

app = FastAPI()


@app.get("/health")
def health_check():
    """Method that is checking if server is running and return Telegram User Info"""
    req = requests.get(f"{URL}getMe")
    return {"Message": req.json(), "status": 200}


@app.route("/set_webhook", methods=["GET", "POST"])
async def set_webhook(request: Request):
    """
    This method is a webhook we use to activate Telegram calls to our server,
    basically telling Telegram to call a specific link when a new message arrives.
    :param request:
    :return:
    """
    if request.headers.get("content-type") == "application/json":
        json_string = await request.json()
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        result = Response(content="Executing")
    else:
        result = Response(content="Error Occurred")
    return result


@check_user_authorization_telegram
@bot.message_handler(commands=["start", "Start", "help", "Help"])
def handle_start_help(message):
    """
    Shows start menu with all supported commands.
    """
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


@check_user_authorization_telegram
@bot.message_handler(commands=["AddExpenseToCurrentMonth", "AECM", "ae"])
def add_expense_to_current_month_handler(message):
    """
    Add expense to current month
    :param message:
    """
    get_worksheet_list_and_register_handler(message, add_current_month_expense_input_category)


@bot.message_handler(commands=["CheckCurrentMonthCategoryExpenses", "CME", "ce"])
def check_category_expenses_handler(message):
    """
    Handler  to check amount of money spent for a specific category
    :param message:
    """
    get_worksheet_list_and_register_handler(message, check_input_category_per_month_expenses)


def check_input_category_per_month_expenses(message, worksheet_list):
    """
    returns Sum spent per category per month
    :param message:
    :param worksheet_list:
    """
    category_num = validate_input_category(message)

    try:
        worksheet = worksheet_list[category_num]
        cols_count = worksheet.col_count
        bot.send_message(message.chat.id,
                         f" {worksheet.title} expenses until today are {worksheet.col_values(cols_count)[1]}")
    except Exception as e:
        bot.reply_to(message, "Please choose the expense category number from message above: ")


def add_current_month_expense_input_category(message, worksheet_list):
    """

    :param message:
    :param worksheet_list:
    """

    category_num = validate_input_category(message)

    try:
        worksheet = worksheet_list[category_num]
        if worksheet in worksheet_list and int(message.text) > 0:
            bot.send_message(message.chat.id, 'You have chosen: ' + str(message.text) + ") " +
                             (worksheet_list[category_num]).title)
            msg = bot.reply_to(message, 'Please enter tag and price as example "Bread: 50": ')
            bot.register_next_step_handler(msg, add_current_month_expense_input_string, worksheet)
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


def add_current_month_expense_input_string(message, worksheet):
    """
    This function represents the process of adding expense to current month
    """
    input_data = message.text.split(':')
    if len(input_data) == 2:
        read_row_str = add_input_data_to_google_sheet(input_data, worksheet)
        bot.send_message(
            message.chat.id, f"{read_row_str} has been added to {worksheet.title} worksheet into"
                             f" {formatted_date.today().strftime('%Y.%m')} file.")
    else:
        bot.send_message(message.chat.id,
                         f"You have entered *** {message.text} *** - wrong input format (Expense:price) or not 2"
                         "parameters in the input")
        msg = bot.reply_to(message, f"Please enter the expense for {str(formatted_date.today().strftime('%Y.%m'))} and "
                                    f"{str(worksheet.title)} category in format expense:price")
        bot.register_next_step_handler(msg, add_current_month_expense_input_string, worksheet)


@bot.message_handler(commands=["CurrentMonthBalance", "CMB", "cb"])
def current_month_balance(message):
    """
    Method that returns 3 different data to User: income, expense and balance
    :param message:
    :return: Current income, expense and balance
    """

    sh = open_google_sheets()
    worksheet = sh.worksheet("Balance")
    bot.send_message(message.chat.id, "Current month income is: " + worksheet.acell('B15').value)
    bot.send_message(message.chat.id, "Current month expenses are: " + worksheet.acell('D15').value)
    bot.send_message(message.chat.id, "Current month balance is: " + worksheet.acell('F1').value)


@bot.message_handler(commands=["AddCurrentMonthIncome", "ACMI", "ai"])
def add_current_month_income(message):
    """
    Add Income to Current Month
    :param message:
    """
    msg = bot.reply_to(message, 'Please Enter your Income following the format: "Salary: 1000"')
    bot.register_next_step_handler(msg, add_current_month_income_input)


def add_current_month_income_input(message):
    """
    Method callback that is inserting the income for current month
    :param message: 
    """
    sh = open_google_sheets()
    worksheet = sh.worksheet("Income")
    input_data = message.text.split(':')
    read_row_str = add_input_data_to_google_sheet(input_data, worksheet)
    bot.send_message(message.chat.id,
                     f"{read_row_str} has been added to {worksheet.title} worksheet into"
                     f" {formatted_date.today().strftime('%Y.%m')} file.")
