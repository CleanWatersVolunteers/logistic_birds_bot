
import json
import tgm
from telegram import InlineKeyboardMarkup, Update
from storage_users import storage_users
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters
import nextgis_connector as nextgis


text_title = """Выберите тип заявки"""

text_cards = """
Карта доступна по ссылке: https://seagull.nextgis.dev/ \n
Заявка создана! Отправьте геопозицию, нажав на "скрепку" ниже
"""

text_help = """
Для того чтобы начать, "расшарьте" свою геолокацию при помощи "скрепки" ниже. Для завершения прекратите трансляцию геолокации и нажмите кнопку "Закрыть заявку"
"""

keyboard_menu_main = {
    "menu_not_driver":"Ищу водителя",
    "menu_driver":"Водитель",
    "menu_help":"Справка",
}
keyboard_menu_main_help = {
    "menu_to_main":"Меню"
}
keyboard_menu_car = {
    "menu_car_not_jeep":"Легковой",
    "menu_car_jeep":"Внедорожник",
    "menu_car_bulk":"Грузовой",
    "menu_car_cancel":"Отмена"
}
keyboard_menu_cargo = {
    "menu_cargo_burd":"Птицы",
    "menu_cargo_bulk":"Груз",
    "menu_cargo_people":"Люди",
    "menu_cargo_cancel":"Отмена"
}

keyboard_menu_request = {
    "menu_request_close":"Закрыть заявку",
    # "menu_request_busy":"Занят",
    "menu_request_help":"Справка",
}
keyboard_menu_request_help = {
    "menu_to_request":"Меню"
}

def keyboard_get_target(query, target_table):
    text = f'{query["message"]["text"]}\n{target_table[query.data]}'
    text += text_cards
    
    username = query["from"]["username"]
    user_id = None
    if storage_users.user_added(username) == False:
        print(f"[..] New user {username}")
        user_id = nextgis.add_point_track(f"{username}")
        if user_id == 0:
            print(f"[!!] Server error for {username}")
            return "Ошибка подключения к серверу!", None
    user_id = storage_users.get_id(username, user_id)
    target = target_table[query.data]
    status = query["message"]["text"].split("\n")[-1].split("(")[0]
    return user_id, text, target, status 

def keyboard_menu_main_handler(query):
    text = ''
    if query.data in keyboard_menu_main:
        text = f'Тип заявки:\n{keyboard_menu_main[query.data]}' 
    if query.data == "menu_driver":
        return text, tgm.make_inline_keyboard(keyboard_menu_car)
    if query.data == "menu_not_driver":
        return text, tgm.make_inline_keyboard(keyboard_menu_cargo)
    if query.data == "menu_help":
        return text_help, tgm.make_inline_keyboard(keyboard_menu_main_help)
    if query.data == "menu_to_main":
        return text_title, tgm.make_inline_keyboard(keyboard_menu_main)
    return text, None 

def keyboard_menu_car_handler(query):
    if query.data == "menu_car_cancel":
        return text_title, tgm.make_inline_keyboard(keyboard_menu_main)
    user_id, text, target, status = keyboard_get_target(query, keyboard_menu_car)
    nextgis.update_details(user_id, target, None, status, "")
    return text, tgm.make_inline_keyboard(keyboard_menu_request)

def keyboard_menu_cargo_handler(query):
    if query.data == "menu_cargo_cancel":
        return text_title, tgm.make_inline_keyboard(keyboard_menu_main)
    user_id, text, target, status = keyboard_get_target(query, keyboard_menu_cargo)
    nextgis.update_details(user_id, None, target, status, "")
    return text, tgm.make_inline_keyboard(keyboard_menu_request)

def keyboard_menu_request_handler(query):
    if query.data == "menu_request_close":
        username = query["from"]["username"]
        if storage_users.user_added(username) == True:
            print(f"[..] Revoking user {username}")
            user_id = storage_users.get_id(username)
            nextgis.move_point_track(
                user_id, 
                0, 
                0,
                'завершено'
            )
        return text_title, tgm.make_inline_keyboard(keyboard_menu_main)

    if query.data == "menu_request_help":  
        return text_help, tgm.make_inline_keyboard(keyboard_menu_request_help)

    if query.data == "menu_to_request":  
        return text_cards, tgm.make_inline_keyboard(keyboard_menu_request)

    return keyboard_menu_request[query.data], tgm.make_inline_keyboard(keyboard_menu_request)

edges = {
    # Main
    "menu_driver":keyboard_menu_main_handler,
    "menu_not_driver":keyboard_menu_main_handler,
    "menu_help":keyboard_menu_main_handler,
    "menu_to_main":keyboard_menu_main_handler,

    "menu_car_jeep":keyboard_menu_car_handler,
    "menu_car_not_jeep":keyboard_menu_car_handler,
    "menu_car_bulk":keyboard_menu_car_handler,
    "menu_car_cancel":keyboard_menu_car_handler,

    "menu_cargo_burd":keyboard_menu_cargo_handler,
    "menu_cargo_bulk":keyboard_menu_cargo_handler,
    "menu_cargo_people":keyboard_menu_cargo_handler,
    "menu_cargo_cancel":keyboard_menu_cargo_handler,

    "menu_request_close":keyboard_menu_request_handler,
    "menu_request_help":keyboard_menu_request_handler,
    "menu_to_request":keyboard_menu_request_handler
}

async def cb_user_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = f""" Здравствуйте @{update["message"]["from"]["username"]}!\n"""+text_title
    keyboard = tgm.make_inline_keyboard(keyboard_menu_main)
    await update.message.reply_text(f'{text}', reply_markup=InlineKeyboardMarkup(keyboard))
    return None

async def cb_reaction_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query["message"]["chat"]["id"]
    if query.data in edges.keys():
        text, keyboard = edges[query.data](query)
        if keyboard:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text=text)
    else:
        print(f"[!!] Got unexpected argument: {query.data}")
    return


