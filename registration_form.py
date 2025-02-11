
import json
import tgm
from telegram import InlineKeyboardMarkup, Update, constants
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters

import re
from nextgis_connector import NextGIS, NextGISUser
from datetime import datetime
import pytz

GET_NOW = lambda: datetime.utcnow().astimezone(pytz.timezone('Etc/GMT-6')).strftime("%d.%m.%Y")
GET_MAP_URL = lambda location: f'https://seagull.nextgis.dev/?zoom=13&center={location[0]}_{location[1]}&layers=233%2C206'

text_parse_mode = constants.ParseMode.MARKDOWN_V2

cfg_max_distance = 0
cfg_max_symbols = 100

text_title_start = "Для создания заявки отправьте геопозицию, нажав на 'скрепку' ниже\n"
text_title_continue = "*Отправьте геопозицию, нажав на 'скрепку' ниже*\n"

text_req_not_found = '❌ Заявки не найдены\. Попробуйте обновить список чуть позже\n'
text_separator = '\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\n'

text_help = f'\n_По всем вопросам и предложениям пишите нам @sosbird\_digital\_team\_bot _ \n'

text_welcome = "Здравствуйте\!\n⚠ Для создания заявки отправьте геопозицию, нажав на 'скрепку' ниже\n"
text_welcome += text_help

text_wait_location = "⚠ Для создания заявки отправьте геопозицию, нажав на 'скрепку' ниже\n"
text_wait_location += text_help

text_select_status = "Выберите тип заявки\n"
text_select_car = "Выберите тип авто\n"
text_select_cargo = "Выберите тип груза\n"

kbd_sel_status = {
    "menu_not_driver":"Ищу водителя",
    "menu_driver":"Водитель",
}
kbd_sel_car = {
    "menu_car_not_jeep":"Легковой",
    "menu_car_jeep":"Внедорожник",
    "menu_car_bulk":"Грузовой",
    "menu_cancel":"Отмена"
}
kbd_sel_cargo = {
    "menu_cargo_burd":"Птицы",
    "menu_cargo_bulk":"Груз",
    "menu_cargo_people":"Люди",
    "menu_cancel":"Отмена"
}

kbd_main_menu = {
    "menu_request_close":"Закрыть заявку",
    "menu_request_update":"Обновить список заявок",
}

kbd_yes_no = {
    "menu_yes":"Да",
    "menu_no":"Нет",
}
################################
# Support functions
################################
md_pattern = r'([\[{}#_*~|`!\.\]=+\-\>()])'
def text_to_markdown(text):
    return re.sub(md_pattern,r'\\\1', text)

def text_from_markdown(text):
    return re.sub(r"\\"+md_pattern, r"\1", text)

def user_in_process(user)->bool:
    if not user:
        return False
    try:
        if user.status != "выполняется":
            return False
        if user.location[0] == 0 or user.location[1] == 0:    
            return False
    except:
        print("[!!] Check user error")
        return False
    # todo add location time checking
    return True

def user_get_create(username):
    user = None
    if username:
        user = NextGIS.get_user(username)
        if not user:
            user = NextGIS.new_user(username)
    return user


def ui_select_menu(user,key=None,message=None):
    if key in kbd_sel_status: # type selected
        text = f'{kbd_sel_status[key]}\n'
        if key == "menu_not_driver":
            text += text_select_cargo
            keyboard = tgm.make_inline_keyboard(kbd_sel_cargo)
        else:
            text += text_select_car
            keyboard = tgm.make_inline_keyboard(kbd_sel_car)

    elif key in kbd_sel_car:  # subtype selected
        user = NextGIS.upd_user(user.name, {
            "car":kbd_sel_car[key],
            "status":message.split('\n')[0],
            "end_route":"выполняется"
        })
        text, keyboard = ui_main_menu(user)
    elif key in kbd_sel_cargo: # subtype selected
        user = NextGIS.upd_user(user.name, {
            "cargo_type":kbd_sel_cargo[key],
            "status":message.split('\n')[0],
            "end_route":"выполняется"
        })
        text, keyboard = ui_main_menu(user)
    else:
        text = text_select_status
        keyboard = tgm.make_inline_keyboard(kbd_sel_status)
    return text, keyboard

def ui_yes_hndl(user,key=None,message=None):
    if user_in_process(user):
        comments = message.split('\n')[1:-1]
        user.comment = ''
        for item in comments:
            user.comment += f'{item}\n'
        NextGIS.upd_user(user.name, {"comment":user.comment})
        return ui_main_menu(user)
    else:
        return ui_welcome(user) 

def ui_no_hndl(user,key=None,message=None):
    if user_in_process(user):
        text, kbd = ui_main_menu(user)
    else:
        text, kbd = ui_welcome(user) 
    return text, kbd

def ui_replace_comment(user,key=None,message=None):
    text = f"Вы ввели новое описание заявки:_\n{text_to_markdown(message[:cfg_max_symbols])}\n_ Сохранить?"
    kbd = tgm.make_inline_keyboard(kbd_yes_no)
    return text, kbd

def ui_main_menu(user,key=None,message=None):
    text = f'*Моя заявка: {user.type}, {user.subtype}, [на карте]({GET_MAP_URL(user.location)})*\n'
    if user.type == "Водитель":
        free_list = NextGIS.get_free_list("Ищу водителя")
    else:
        free_list = NextGIS.get_free_list("Водитель")
    if user.comment != None:
        text +=f'_*{text_to_markdown(user.comment)}*_\n'
    if free_list:
        if user.type == "Водитель":
            text += "Ждут помощи:\n"
        else:
            text += "Вам готовы помочь:\n"
        text += text_separator
        for item in free_list:
            distance = NextGIS.get_distance(item.location,user.location)
            if cfg_max_distance > 0 and cfg_max_distance < distance:
                continue
            map_url = GET_MAP_URL(item.location)
            hour = item.hour_loc
            minute = item.minute_loc
            text += f'{item.subtype} {distance}км, был в {hour:02d}:{minute:02d}\n'
            if item.comment != None:
                text += f'_{text_to_markdown(item.comment)}_\n'
            text += f'[написать](https://t.me/{text_to_markdown(item.name)}), [на карте]({map_url})\n\n'

        text = text[:-1]
        text += text_separator
    else:
        text += text_req_not_found

    # text += f'Все доступные заявки можно посмотреть на [карте]({GET_MAP_URL(user.location)})\n\n'
    text += f'⚠ *Вы можете добавить описание заявки в текстовом поле ниже \(максимум {cfg_max_symbols} символов\), также уточняйте детали в личных сообщениях*\n'
    # text += '⚠ *Пожалуйста, подробности о маршруте уточняйте у пользователя из заявки*\n'
    text += text_help
    keyboard = tgm.make_inline_keyboard(kbd_main_menu)
    return text, keyboard

def ui_welcome(user)->():
    text = text_welcome
    return text, None

################################
# Keyboard handlers
################################
def kbd_cancel_hndl(user,key=None,message=None):
    text = text_select_status
    keyboard = tgm.make_inline_keyboard(kbd_sel_status)
    return text, keyboard

def kbd_close_hndl(user,key=None,message=None):
    NextGIS.complete_user(user.name)
    text = text_wait_location
    return text, None

kbd_handlers_list = {
    "menu_cancel":kbd_cancel_hndl,

    "menu_not_driver":ui_select_menu,
    "menu_driver":ui_select_menu,

    "menu_car_not_jeep":ui_select_menu,
    "menu_car_jeep":ui_select_menu,
    "menu_car_bulk":ui_select_menu,

    "menu_cargo_burd":ui_select_menu,
    "menu_cargo_bulk":ui_select_menu,
    "menu_cargo_people":ui_select_menu,

    "menu_request_close":kbd_close_hndl,
    "menu_request_update":ui_main_menu,

    "menu_yes":ui_yes_hndl,
    "menu_no":ui_no_hndl,
}

async def cb_user_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # message process
    message = None
    if update.edited_message:
        message = update.edited_message
    if not message and update.message:
        message = update.message
    if not message:
        print("[!!] Unknown error")
        return None

    text = "Ошибка\!"
    keyboard = None

    # find user
    username = message.from_user.username
    user = user_get_create(username)
    if not user:
        print("[!!] Ошибка пользователя!", username)
        await message.reply_text(text, parse_mode=text_parse_mode)
        return None

    # update location
    print("[..] GEO from user", username)
    NextGIS.upd_user(username, {
        "long":message.location.longitude,
        "lat":message.location.latitude
    })

    # show menu
    if not user_in_process(user) and update.message: # first request 
        text, keyboard = ui_select_menu(user)
        try:
            if keyboard:
                await message.reply_text(text, parse_mode=text_parse_mode, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await message.reply_text(text, parse_mode=text_parse_mode, disable_web_page_preview=True)
        except Exception as e:
            print('[!!] Exception ', e)
    return None

async def cb_user_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # find user
    username = update["message"]["from"]["username"]
    user = user_get_create(username)
    if not user:
        print("[!!] Ошибка пользователя!", username)
        text = "Ошибка\!"
        await update.message.reply_text(text, parse_mode=text_parse_mode)
        return None

    # show menu
    if user_in_process(user):
        text, keyboard = ui_replace_comment(user, message=update.message.text)
        # text, keyboard = ui_main_menu(user)
    else:
        text, keyboard = ui_welcome(user)
    try:
        if keyboard:
            await update.message.reply_text(text, parse_mode=text_parse_mode, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode=text_parse_mode, disable_web_page_preview=True)
    except Exception as e:
        print('[!!] Exception ', e)

async def cb_reaction_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # find user
    username = query.from_user.username
    user = user_get_create(username)
    if not user:
        print("[!!] Ошибка пользователя!", username)
        text = "Ошибка\!"
        await query.edit_message_text(text=text, parse_mode=text_parse_mode)
        return None

    # show menu
    if query.data in kbd_handlers_list.keys():
        text, keyboard = kbd_handlers_list[query.data](user=user, key=query.data, message=query.message.text)
    else:
        print(f"[!!] Got unexpected argument: {query.data}")
        text = "Ошибка\!"
        keyboard = None

    try:
        if keyboard:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode, disable_web_page_preview=True)
    except Exception as e:
        print('[!!] Exception ', e)
    return None

