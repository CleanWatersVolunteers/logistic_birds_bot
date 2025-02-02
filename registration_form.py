import json
import tgm
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, JobQueue, CallbackContext
##, Filters, Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import re
from nextgis_connector import NextGIS
import datetime
import pytz

GET_NOW = lambda: datetime.datetime.utcnow().astimezone(pytz.timezone('Etc/GMT-6')).strftime("%d.%m.%Y")
GET_MAP_URL = lambda long, lat: f'https://seagull.nextgis.dev/?zoom=13&center={long}_{lat}&layers=233%2C206'

text_parse_mode = constants.ParseMode.MARKDOWN_V2

MAX_DISTANCE_LIMIT = 20 #км
EXPERIMENTAL_MODE = False  #подключает экспериментальные функции из модуля experimental

text_title_start = "*_Для создания заявки отправьте геопозицию_*, нажав на 'скрепку' ниже\n"
text_title_continue = "*Отправьте геопозицию*, нажав на 'скрепку' ниже\n"

text_req_not_found = 'Встречные заявки не найдены 😞 Попробуйте обновить список чуть позже\n'
text_separator = '\n' ##\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-

text_select_status = "Выберите тип заявки\n"
text_select_car = "Выберите тип авто\n"
text_select_cargo = "Выберите тип груза\n"

kbd_enable_location = {
    "menu_enable_location":"🛰 Включить трансляцию геопозиции"
}

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

def escape_markdown(text):
    """функция для экранирования символов перед отправкой в маркдауне Telegram"""
    pattern = r"([_*~|`!\.])" ##was r"(\\[_*\[\]()~|`!\.])"
    text = re.sub(r"\\"+pattern, r"\1", text) #размаркирование, на всякий случай, чтобы не получилось двойное
    text = re.sub(pattern, r"\\\1", text)
    return text

def delete_olds_on_map():
    old_list = NextGIS.get_old_list()
    if old_list:
        for item in old_list:
            item_username = item["fields"]["contact_info"].replace('https://t.me/','')
            NextGIS.upd_user(item_username, {
                    "car":None,
                    "cargo_type":None,
                    "status":None,
                    "lat":0,
                    "long":0,
                    "end_route":"завершено"
            })


def main_menu(username, key=None, message=None, debug_context=None):

    ## delete_olds_on_map()
    
    user = NextGIS.get_user(username)
    if not user:
        # todo add process
        pass

    text = f'*Ваша заявка: * {user["status"]}, '

    if user["status"] == "Водитель":
        request_status = "Ищу водителя"
        text += f'{user["car"]}\n'
    else:
        request_status = "Водитель"
        text += f'{user["cargo_type"]}\n'

    max_distance_limit_text = f' в пределах {MAX_DISTANCE_LIMIT} км' if MAX_DISTANCE_LIMIT>0 else ''
    text += f'*Встречные заявки{max_distance_limit_text}: *\n'
                                                  
    text += text_separator

    free_list = NextGIS.get_free_list(request_status, user, MAX_DISTANCE_LIMIT)
    if free_list:
        req_text=''
        date_now = GET_NOW().split('.')
        for item in free_list:
            print(f'\n[..] After get_free_list: {item=}')
            contact_info = item["fields"]["contact_info"]
            link = re.search("https://t.me/",contact_info)
            if link and item["fields"]["long"] != 0 and item["fields"]["lat"] != 0:
                map_url = GET_MAP_URL(item["fields"]["long"], item["fields"]["lat"])
                hour = item["fields"]["dt_coord"]["hour"]
                minute = item["fields"]["dt_coord"]["minute"]
                date_coord = datetime.datetime(
                    item["fields"]["dt_coord"]["year"], 
                    item["fields"]["dt_coord"]["month"], 
                    item["fields"]["dt_coord"]["day"],
                    hour,
                    minute
                )
                date_now = datetime.datetime.now()

                delta = (date_now - date_coord).total_seconds() / 3600
                if int(delta) < 12:
                    req_text += f'{request_status}'
                    if request_status == "Водитель":
                        req_text += f', {item["fields"]["car"]}'
                    else:
                        req_text += f', {item["fields"]["cargo_type"]}'
                    item_username = contact_info.replace('https://t.me/','') ##issues/11
                    item_username = escape_markdown(item_username)
                    req_text += f'\n@{item_username}' 
                    if "dt_coord" in item["fields"]:
                        req_text += f' был в {item["fields"]["dt_coord"]["hour"]:02d}:{item["fields"]["dt_coord"]["minute"]:02d}'
                    req_text += f' [на карте]({map_url})'
                    
                    req_text += f' в {item["dist"]}км' if item["dist"] else ''                         

                    req_text += '\n\n'
        if req_text:
            text += req_text[:-1]
            text += '\nВыберите заявку, свяжитесь с контактом в ней\. Если договоритесь с ним, то закройте свою заявку, чтобы она не отвлекала остальных волонтеров 🙏'#issues/12
        else:
            text += text_req_not_found
    else:
        text = text_req_not_found
    text += text_separator
    print(f'\n\n[..] After get_free_list: {text=}')
    if "lat" in user and "long" in user:
        map_url = "https:\/\/seagull\.nextgis\.dev\/"
        if user["lat"] != 0 and user["long"] != 0:
            map_url = GET_MAP_URL(user["long"], user["lat"])
        text += f'Также доступные заявки можно посмотреть на [карте]({map_url})'
        text += f'\n_Вопросы и предложения пишите нам через бота @sosbird\_digital\_team\_bot _ \n'
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
    text = escape_markdown(message)
    text = f'RESTART\n{text}\n__Вы закрыли заявку__\n\n'
    keyboard = None ##was: tgm.make_inline_keyboard(kbd_sel_status)
    return text, keyboard


async def cb_user_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = None
    is_updated_message = False
                           
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
        text = "\nОшибка добавления пользователя\!"
        await message.reply_text(text, parse_mode=text_parse_mode)
        return None

    # в любом случае обновляем геопозицию в ГИС
    NextGIS.upd_user(username, {
        "long":message.location.longitude,
        "lat":message.location.latitude
    })

    #ToDo experiment запуск трасляции геопозиции на время, если включен экспериментальный режим
    if EXPERIMENTAL_MODE:
        from experimental import set_geo_translation_timer
        set_geo_translation_timer(context, message)
        await update.message.reply_text(
            f"🚀 Трансляция активирована на {context.user_data['live_period']} секунд!",
            reply_markup=ReplyKeyboardRemove()
        )
        
    # реакция пользователю
    if not is_updated_message: #только если получено первичное сообщение с геопозицией, а не автообновление
        if user["end_route"] == "выполняется":
                                                                          
            kbd_cargo_hndl
            text, keyboard = main_menu(username, key=None,message=None, debug_context='cb_user_location::if not is_updated_message')
            if text == message.text:
                print("\n\n[--] Got the same text. Skip reply")
            else:
                                                                                           
                if keyboard:
                    await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await message.reply_text(text, parse_mode=text_parse_mode)
        else:
            print(f'\n[..] не выполняется - или новый user или было завершено')
            text = text_select_status
            keyboard = tgm.make_inline_keyboard(kbd_sel_status)
                                                                  
            await message.reply_text(text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))

    return None

async def cb_user_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update["message"]["from"]["username"]
    await cb_user_register_form(username, update.message)

async def cb_user_register_form(username, source_message) -> None:
    user = NextGIS.get_user(username)

    text = "👋 Здравствуйте\!\n"
    if not username:
        text += f'‼️ Чтобы пользоваться этим ботом, заполните поле username в настройках приложения Telegram ‼️'

    text += f'\n_По всем вопросам и предложениям пишите нам @sosbird\_digital\_team\_bot_\n\n'

    if "end_route" in user:
        if user["end_route"] == "выполняется":
            text += text_title_continue
            # todo show menu instead
        else:
            text += text_title_start
    else:
        text += text_title_start
                                                                     

    reply_markup = None
    if EXPERIMENTAL_MODE:
        keyboard = tgm.make_inline_keyboard(kbd_enable_location)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
    await source_message.reply_text(text, parse_mode=text_parse_mode, reply_markup=reply_markup)

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

async def cb_reaction_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query
    await query.answer()

    if query.data == 'menu_enable_location':#эта ветка сработает только в экпериментальном режиме
        # Создаем reply-клавиатуру с кнопкой для отправки геопозиции
        button = KeyboardButton(
            text="📍 Транслировать геопозицию",
            request_location=True,
        )
        reply_markup = ReplyKeyboardMarkup(
            [[button]], 
            resize_keyboard=True, 
            one_time_keyboard=True
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Пожалуйста, нажмите кнопку \n📍 Транслировать геопозицию\nниже",
            reply_markup=reply_markup
        )
        return None
    
    username = query.from_user.username
    user = NextGIS.get_user(username)
    if not user:
        user = NextGIS.new_user(username)
    if not user:
        print("[!!] Ошибка добавления пользователя!", username)
        text = "\nОшибка добавления пользователя"
        await query.edit_message_text(text=text, parse_mode=text_parse_mode)
        return None
    
    if query.data in kbd_handlers_list.keys():
        text, keyboard = kbd_handlers_list[query.data](username=username, key=query.data, message=query.message.text)
        
        ###text = escape_markdown(text)
        ##was text = text.f('\-','-').replace('-','\-').replace('\.','.').replace('.','\.')
        text_to_compare =  text[:text.find('можно посмотреть')] ##.replace('[','').replace(']','')

        old_text = update.callback_query.message.text if update.callback_query.message else ''
        ###old_text = escape_markdown(old_text)
##was old_text=old_text.replace('\-','-').replace('-','\-').replace('.','\.')
        old_text_to_compare = old_text[:old_text.find('можно посмотреть')]
                                                                  

        if old_text_to_compare == text_to_compare:
            print("\n[--] Got the same text. Skip reply")
            return None
        
        ##ToDo переделать на отправку кнопки "Начать снова."
        if text.startswith('RESTART'):
            to_restart_bot = True
            text = text[len('RESTART'):]
        else:
            to_restart_bot = False

        if keyboard:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(text=text, parse_mode=text_parse_mode)

        if to_restart_bot:
            print("\n\n[/] Before await cb_user_register_form(username, update.callback_query.message)")
            await cb_user_register_form(username, update.callback_query.message)
            print("\n\n[/] After await cb_user_register_form(username, update.callback_query.message)")
        
    else:
        print(f"\n\n[!!] Got unexpected argument: {query.data=}")
    return None
