import json
import tgm
from telegram import InlineKeyboardMarkup, Update, constants
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters

import re
from nextgis_connector import NextGIS
from datetime import datetime
import pytz

GET_NOW = lambda: datetime.utcnow().astimezone(pytz.timezone('Etc/GMT-6')).strftime("%d.%m.%Y")
GET_MAP_URL = lambda long, lat: f'https://seagull.nextgis.dev/?zoom=13&center={long}_{lat}&layers=233%2C206'

text_parse_mode = constants.ParseMode.MARKDOWN_V2


text_title_start = "Для создания заявки отправьте геопозицию, нажав на 'скрепку' ниже\n"
text_title_continue = "Отправьте геопозицию, нажав на 'скрепку' ниже\n"

text_req_not_found = 'Заявки не найдены\. Попробуйте обновить список чуть позже\n'
text_separator = '\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\n'

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

# todo add "если у вас остались вопросы или предложения по работе бота, обязательно свяжитесь с нами: @sosbird_digital_team_bot"
# todo menu: поиск/выполняется/завершен
kbd_main_menu = {
    "menu_request_close":"Закрыть заявку",
    "menu_request_update":"Обновить список заявок",
}

def main_menu(username,key=None,message=None, debug_context=None):
    user = NextGIS.get_user(username)
    if not user:
        # todo add process
        pass

    text = f'Ваша заявка: {user["status"]}, '

    if user["status"] == "Водитель":
        request_status = "Ищу водителя"
        text += f'{user["car"]}\n'
    else:
        request_status = "Водитель"
        text += f'{user["cargo_type"]}\n'

    # time_tz = lambda tz: datetime.now(pytz.timezone(tz))
    # status_time = lambda : time_tz('Etc/GMT-3').strftime('%d-%m-%Y %H:%M')

    text += f'Вам готовы помочь:\n'
    text += text_separator

    old_list = NextGIS.get_old_list() #ToDo
    if old_list:
        for item in old_list:
            contact_info = item["fields"]["contact_info"]
            item_username = contact_info.replace('https://t.me/','')
            print(f'\n{item=}\n{item_username=}')
            NextGIS.upd_user(item_username, {
                    "car":None,
                    "cargo_type":None,
                    "status":None,
                    "lat":0,
                    "long":0,
                    "end_route":"завершено"
            })

    free_list = NextGIS.get_free_list(request_status)
    if free_list:
        req_text=''
        date_now = GET_NOW().split('.')
        for item in free_list:
            contact_info = item["fields"]["contact_info"]
            link = re.search("https://t.me/",contact_info)
            if link and item["fields"]["long"] != 0 and item["fields"]["lat"] != 0:
                map_url = GET_MAP_URL(item["fields"]["long"], item["fields"]["lat"])
                hour = item["fields"]["dt_coord"]["hour"]
                minute = item["fields"]["dt_coord"]["minute"]
                date_coord = datetime(
                    item["fields"]["dt_coord"]["year"], 
                    item["fields"]["dt_coord"]["month"], 
                    item["fields"]["dt_coord"]["day"],
                    hour,
                    minute
                )
                date_now = datetime.now()

                delta = (date_now - date_coord).total_seconds() / 3600
                if int(delta) < 12:
                    req_text += f'{request_status},'
                    if request_status == "Водитель":
                        req_text += f'{item["fields"]["car"]}'
                    else:
                        req_text += f'{item["fields"]["cargo_type"]}'
                    username_masked = username.replace('_', '\_')
                    req_text += f'\n@{username_masked}' ##was: f'\n@{contact_info[link.span()[1]:]}'
                    if "dt_coord" in item["fields"]:
                        req_text += f' был в {item["fields"]["dt_coord"]["hour"]:02d}:{item["fields"]["dt_coord"]["minute"]:02d}'
                    req_text += f' [на карте]({map_url})'
                    req_text += '\n\n'
        if req_text:
            text += req_text[:-1]
        else:
            text += text_req_not_found
    else:
        text = text_req_not_found
    text += text_separator
    print(f'\n\nAfter get_free_list: {text=}')
    if "lat" in user and "long" in user:
        map_url = "https://seagull.nextgis.dev/"
        if user["lat"] != 0 and user["long"] != 0:
            map_url = GET_MAP_URL(user["long"], user["lat"])
        text += f'Также доступные заявки можно посмотреть на [карте]({map_url})'
        keyboard = tgm.make_inline_keyboard(kbd_main_menu)
    else:
        text += text_title_continue
        keyboard = None
    
    print(f'\n\nBefore end of main_menu(,,{debug_context=}): {text=}; {keyboard=}')
    return text, keyboard



def kbd_cancel_hndl(username,key=None,message=None):
    text = text_select_status
    keyboard = tgm.make_inline_keyboard(kbd_sel_status)
    return text, keyboard


def kbd_status_hndl(username,key=None,message=None):
    if not key in kbd_sel_status:
        print("\n\n[!!] Incorrect key", key, kbd_sel_status)
        return kbd_cancel_hndl(username,key,message)
    text = f'{kbd_sel_status[key]}\n'
    if key == 'menu_not_driver':
        text += text_select_cargo
        keyboard = tgm.make_inline_keyboard(kbd_sel_cargo)
    elif key == 'menu_driver':
        text += text_select_car
        keyboard = tgm.make_inline_keyboard(kbd_sel_car)
    else:
        return kbd_cancel_hndl(username,key,message)
    return text, keyboard


def kbd_car_hndl(username,key=None,message=None):
    if key in kbd_sel_car and message:
        NextGIS.upd_user(username, {
            "car":kbd_sel_car[key],
            "cargo_type":None,
            "status":message.split('\n')[0],
            "end_route":"выполняется"
        })
        res = main_menu(username, key=None,message=None, debug_context='kbd_car_hndl')
        print(f'\n\n[..] kbd_car_hndl:: after main_menu...')
    else:
        print("[!!] Incorrect key", key, kbd_sel_car)
        res = kbd_cancel_hndl(username,key,message)
    return res

def kbd_cargo_hndl(username,key=None,message=None):
    if key in kbd_sel_cargo and message:
        NextGIS.upd_user(username, {
            "car":None,
            "cargo_type":kbd_sel_cargo[key],
            "status":message.split('\n')[0],
            "end_route":"выполняется"
        })
        res = main_menu(username, key=None,message=None, debug_context='kbd_cargo_hndl')
        print(f'\n\n[..] kbd_cargo_hndl:: after main_menu...')
    else:
        print("\n[!!] Incorrect key", key, kbd_sel_cargo)
        res =  kbd_cancel_hndl(username,key,message)
    return res

def kbd_close_hndl(username,key=None,message=None):
    NextGIS.upd_user(username, {
            "car":None,
            "cargo_type":None,
            "status":None,
            "lat":0,
            "long":0,
            "end_route":"завершено"
    })
    # await message.reply_text('\nВы закрыли заявку. Если Вы нашли помощника, пожалуйста, будьте с ним на связи!', parse_mode=text_parse_mode)
    text = 'RESTART_BOT'
    keyboard = None ##was: tgm.make_inline_keyboard(kbd_sel_status)
    return text, keyboard


async def cb_user_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = None
    is_updated_message = False
    # print(f'\n{update=}')
    if update.edited_message:
        message = update.edited_message
        is_updated_message = True
    if not message and update.message:
        message = update.message

    if not message:
        print("\n\n[!!] Unknown error")
        return None

    username = message.from_user.username
    user = None
    if username:
        user = NextGIS.get_user(username)
        if not user:
            user = NextGIS.new_user(username)
    else:
        print("\n\n[!!] Username not found", update)

    if not user:
        print("\n\n[!!] Ошибка добавления пользователя!", username)
        text = "Ошибка!"
        await message.reply_text(text, parse_mode=text_parse_mode)
        return None

    print("\n[..] Geo from user", username)
    # print(f'[..] {user=}')

##{AK упрощаю код, не было отправки в гис при новой заявке после завершено
    ##{{старый код
    # If first request
    # if not user.get("end_route"):
    #     print(f'\n[..] if not "end_route" in user')
    #     NextGIS.upd_user(username, {
    #         "long":message.location.longitude,
    #         "lat":message.location.latitude
    #     })
    #     if not is_updated_message:
    #         text = text_select_status
    #         keyboard = tgm.make_inline_keyboard(kbd_sel_status)
    #         print(f'[..] Sending {keyboard=}; {text=}...')
    #         await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
    #     return None

    # In process
    # if user["end_route"] == "выполняется":
    #     print(f'\n[..] user["end_route"] == "выполняется"')
    #     NextGIS.upd_user(username, {
    #         "long":message.location.longitude,
    #         "lat":message.location.latitude
    #     })
    #     if not is_updated_message:
    #         text, keyboard = main_menu(username)
    #         print(f'\n[..] Sending {keyboard=}; {text=}...')
    #         if keyboard:
    #             await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
    #         else:
    #             await message.reply_text(text, parse_mode=text_parse_mode)
    ##}}старый код

    # в любом случае обновляем геопозицию в ГИС
    NextGIS.upd_user(username, {
        "long":message.location.longitude,
        "lat":message.location.latitude
    })

    # реакция пользователю
    if not is_updated_message: #только если получено первичное сообщение с геопозицией, а не автообновление
        if user["end_route"] == "выполняется":
            print(f'\n[..] user["end_route"] == "выполняется"')
            kbd_cargo_hndl
            text, keyboard = main_menu(username, key=None,message=None, debug_context='cb_user_location::if not is_updated_message')
            if text == message.text:
                print("\n\n[--] Got the same text. Skip reply")
            else:
                print(f'\n\n[..] cb_user_location:: if not is_updated_message: Sending...')
                if keyboard:
                    await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await message.reply_text(text, parse_mode=text_parse_mode)
        else:
            print(f'\n[..] не выполняется - или новый user или было завершено')
            text = text_select_status
            keyboard = tgm.make_inline_keyboard(kbd_sel_status)
            print(f'\n\n[..] cb_user_location:: else: Sending...')
            await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))

    print(f'\n\nBefore end of cb_user_location()')
    return None

    ##}AK упрощаю код, не было отправки в гис при новой заявке после завершено


# delete this dublicate from AI: ниже упрощенный вариант, чтобы не писать дублирую
    # if not is_updated_message:
    #     # main menu
    #     text = text_select_status
    #     keyboard = tgm.make_inline_keyboard(kbd_sel_status)
    #     await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))

async def cb_user_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update["message"]["from"]["username"]
    await cb_user_register_form(username, update.message)


async def cb_user_register_form(username, source_message) -> None:
    user = NextGIS.get_user(username)

    text = "Здравствуйте\!\n"
    text += f'_По всем вопросам и предложениям пишите нам @sosbird\_digital\_team\_bot_\n\n'
    # text += "Вопросы и предложения по работе бота обязательно пишите нам : @sosbird_digital_team_bot\n\n"
    if "end_route" in user:
        if user["end_route"] == "выполняется":
            text += text_title_continue
            # todo show menu instead
        else:
            text += text_title_start
    else:
        text += text_title_start
    await source_message.reply_text(text, parse_mode=text_parse_mode)

kbd_handlers_list = {
    "menu_cancel":kbd_cancel_hndl,

    "menu_not_driver":kbd_status_hndl,
    "menu_driver":kbd_status_hndl,

    "menu_car_not_jeep":kbd_car_hndl,
    "menu_car_jeep":kbd_car_hndl,
    "menu_car_bulk":kbd_car_hndl,

    "menu_cargo_burd":kbd_cargo_hndl,
    "menu_cargo_bulk":kbd_cargo_hndl,
    "menu_cargo_people":kbd_cargo_hndl,

    "menu_request_close":kbd_close_hndl,
    "menu_request_update":main_menu,
}

def escape_markdown(text):
    """функция для экранирования символов перед отправкой в маркдауне Telegram"""
    pattern = r"([_*\[\]()~|`])"
    return re.sub(pattern, r"\\\1", text)

async def cb_reaction_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f'\n\n[..] cb_reaction_button...')
    old_text = update.callback_query.message.text if update.callback_query.message else ''

    query = update.callback_query
    await query.answer()

    username = query.from_user.username
    user = NextGIS.get_user(username)
    if not user:
        user = NextGIS.new_user(username)
    if not user:
        print("[!!] Ошибка добавления пользователя!", username)
        text = "Ошибка"
        await query.edit_message_text(text=text, parse_mode=text_parse_mode)
        return None
    
    if query.data in kbd_handlers_list.keys():
        text, keyboard = kbd_handlers_list[query.data](username=username, key=query.data, message=query.message.text)
        print(f'\n\ncb_reaction_button:: after kbd_handlers_list...')
        if text=='RESTART_BOT':
            print("\n\n[/] Before await cb_user_register_form(username, update.callback_query.message)")
            await cb_user_register_form(username, update.callback_query.message)
            print("\n\n[/] After await cb_user_register_form(username, update.callback_query.message)")
            return None
        
        text_href_pos = text.find('можно посмотреть')
        text_to_compare = text[:text_href_pos] ##.replace('[','').replace(']','')
        print(f'\ntext_to_compare=\n{text_to_compare}\n=')

        old_text=old_text.replace('-','\-').replace('.','\.')
        old_text_to_compare = old_text[:old_text.find('можно посмотреть')]
        print(f'\nold_text_to_compare=\n{old_text_to_compare}\n=')

        if old_text_to_compare == text_to_compare:
            print("\n\n[--] Got the same text. Skip reply")
            return None
        
        if keyboard:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode)
    else:
        print(f"\n\n[!!] Got unexpected argument: {query.data=}")
    return None

