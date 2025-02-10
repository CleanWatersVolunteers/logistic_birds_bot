import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters
import registration_form
from nextgis_connector import NextGIS
from datetime import datetime

f = open('token', 'r')
TELEGRAM_BOT_TOKEN = f.read()
f.close()

NextGIS.init()


async def main() -> None:
	"""Run the bot."""
	# Create the Application and pass it your bot's token.
	application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

	application.add_handler(CommandHandler("start", registration_form.cb_user_register))
	application.add_handler(MessageHandler(filters.TEXT, registration_form.cb_user_register))
	application.add_handler(CallbackQueryHandler(registration_form.cb_reaction_button))
	application.add_handler(MessageHandler(filters.LOCATION, registration_form.cb_user_location))


	await application.initialize()
	await application.start()
	await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

	print("[OK] Bot enabled")

	while True:
		await asyncio.sleep(6*3600)
		NextGIS.user_clear_old()

	await application.updater.stop()
	print("[OK] Bot disabled")

	await application.shutdown()


if __name__ == "__main__":
	asyncio.run(main())

