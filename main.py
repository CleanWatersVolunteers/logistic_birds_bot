import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters
import registration_form
from storage_users import storage_users
import nextgis_connector as nextgis
from datetime import datetime

f = open('token', 'r')
TELEGRAM_BOT_TOKEN = f.read()
f.close()

storage_users.init()

# async def cb_user_info_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     username = update["message"]["from"]["username"]
#     if storage_users.user_added(username) == True:
#         print(f"[..] Revoking user {username}")
#         user_id = storage_users.get_id(username)
#         nextgis.move_point_track(
#             user_id, 
#             0, 
#             0,
#             'завершено'
#         )

async def cb_user_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "message" in update.to_dict():
        message = update.message
    if "edited_message" in update.to_dict():
        message = update.edited_message
    username = message.from_user.username
    user_not_new = storage_users.user_added(username)
    print(f'[OK] Location received from user: {username}. Known: {user_not_new}')

    if user_not_new:
        user_id = storage_users.get_id(username)
        print(f"[..] Known user {username}. ID {user_id}")

        # nextgis.move_point_track(
        #     user_id, 
        #     38.1, 
        #     50.2,
        #     'выполняется'
        # )
        nextgis.move_point_track(
            user_id, 
            message.location.latitude,
            message.location.longitude,
            'выполняется'
        )

async def main() -> None:
	"""Run the bot."""
	# Create the Application and pass it your bot's token.
	application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

	application.add_handler(CommandHandler("start", registration_form.cb_user_register))
	application.add_handler(MessageHandler(filters.TEXT, registration_form.cb_user_register))
	application.add_handler(CallbackQueryHandler(registration_form.cb_reaction_button))
	application.add_handler(MessageHandler(filters.LOCATION, cb_user_location))

	# application.add_handler(CommandHandler("stop", cb_user_info_revoke))
	
	

	await application.initialize()
	await application.start()
	await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

	print("[OK] Bot enabled")

	while True:
		await asyncio.sleep(5*60)

	await application.updater.stop()
	print("[OK] Bot disabled")

	await application.shutdown()


if __name__ == "__main__":
	asyncio.run(main())

