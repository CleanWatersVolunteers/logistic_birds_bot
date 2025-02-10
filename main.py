import asyncio
import os
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

	i=0
	d_commands = []
	for i in range(0, 19):
			d_commands.append(f'ClickMe{i}')
	application.add_handler(CommandHandler(d_commands, registration_form.cmd_d_hndl))
	
	application.add_handler(CommandHandler("start", registration_form.cb_user_register))
	application.add_handler(MessageHandler(filters.TEXT, registration_form.cb_user_comment))
	## application.add_handler(MessageHandler(filters.TEXT, registration_form.cb_user_register))
	application.add_handler(CallbackQueryHandler(registration_form.cb_reaction_button))
	application.add_handler(MessageHandler(filters.LOCATION, registration_form.cb_user_location))

	# application.add_handler(CommandHandler("stop", cb_user_info_revoke))
	
	await application.initialize()
	await application.start()
	await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

	print("[OK] Bot enabled")

	while True:
		await asyncio.sleep(1*3600)
		NextGIS.user_clear_old()
	
	await application.updater.stop()
	print("[OK] Bot disabled")

	await application.shutdown()

if __name__ == "__main__":
	asyncio.run(main())

