import logging
import re
import traceback
from datetime import datetime

import utils
import static
from classes.reminder import Reminder

log = logging.getLogger("bot")


def get_reminders_string(user, database, previous=False):
	bldr = utils.str_bldr()

	reminders = database.get_user_reminders(user)
	if len(reminders):
		if previous:
			bldr.append("Your previous reminders:")
		else:
			bldr.append("Your current reminders:")
		bldr.append("\n\n")

		if len(reminders) > 1:
			bldr.append("[Click here to delete all your reminders](")
			bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Remove All", "RemoveAll!"))
			bldr.append(")\n\n")

		log.debug(f"Building list with {len(reminders)} reminders")
		bldr.append("|Source|Message|Date|Remove|\n")
		bldr.append("|-|-|-|:-:|\n")
		for reminder in reminders:
			bldr.append("|")
			bldr.append(reminder.source)
			bldr.append("|")
			bldr.append(reminder.message)
			bldr.append("|")
			bldr.append(utils.render_time(reminder.target_date))
			bldr.append("|")
			bldr.append("[Remove](")
			bldr.append(utils.build_message_link(static.ACCOUNT_NAME, "Remove", f"Remove! {reminder.db_id}"))
			bldr.append(")")
			bldr.append("|\n")

			if utils.bldr_length(bldr) > 9000:
				log.debug("Message length too long, returning early")
				bldr.append("\nToo many reminders to display.")
				break
	else:
		bldr.append("You don't have any reminders.")

	return bldr


def process_remind_me(message, database):
	log.info("Processing RemindMe message")
	time = utils.find_reminder_time(message.body)
	if time is None:
		log.debug("Couldn't find time")

	message_text = utils.find_reminder_message(message.body)
	if message_text is None:
		log.debug("Couldn't find message, defaulting to message link")
		message_text = utils.message_link(message.id)

	reminder = Reminder(
		source=utils.message_link(message.id),
		message=message_text,
		user=message.author.name,
		requested_date=utils.datetime_force_utc(datetime.utcfromtimestamp(message.created_utc)),
		time_string=time
	)
	if not reminder.valid:
		log.debug("Reminder not valid, returning")
		return [reminder.result_message]

	if not database.save_reminder(reminder):
		log.info("Something went wrong saving the reminder")
		return ["Something went wrong saving the reminder"]

	return reminder.render_confirmation()


def process_remove_reminder(message, database):
	log.info("Processing remove reminder message")
	bldr = utils.str_bldr()

	ids = re.findall(r'remove!\s(\d+)', message.body, flags=re.IGNORECASE)
	if len(ids) == 0:
		bldr.append("I couldn't find a reminder id to remove.")
	else:
		reminder = database.get_reminder(ids[0])
		if reminder is None or reminder.user != message.author.name:
			bldr.append("It looks like you don't own this reminder or it doesn't exist.")
		else:
			if database.delete_reminder(reminder):
				bldr.append("Reminder deleted.")
			else:
				bldr.append("Something went wrong, reminder not deleted.")

	bldr.append(" ")

	bldr.extend(get_reminders_string(message.author.name, database))

	return bldr


def process_remove_all_reminders(message, database):
	log.info("Processing remove all reminders message")

	current_reminders = get_reminders_string(message.author.name, database, True)

	reminders_deleted = database.delete_user_reminders(message.author.name)

	bldr = utils.str_bldr()
	if reminders_deleted != 0:
		bldr.append("Deleted **")
		bldr.append(str(reminders_deleted))
		bldr.append("** reminders.\n\n")

	bldr.extend(current_reminders)

	return bldr


def process_get_reminders(message, database):
	log.info("Processing get reminders message")
	return get_reminders_string(message.author.name, database)


def process_delete_comment(message, reddit, database):
	log.info("Processing delete comment")
	bldr = utils.str_bldr()

	ids = re.findall(r'delete!\s(\w+)', message.body, flags=re.IGNORECASE)
	if len(ids) == 0:
		bldr.append("I couldn't find a comment id to delete.")
	else:
		bldr.append("")

	return bldr


def process_message(message, reddit, database):
	log.info(f"Message /u/{message.author.name} : {message.id}")
	body = message.body.lower()

	bldr = None
	if "remindme" in body:
		bldr = process_remind_me(message, database)
	elif "myreminders!" in body:
		bldr = process_get_reminders(message, database)
	elif "remove!" in body:
		bldr = process_remove_reminder(message, database)
	elif "removeall!" in body:
		bldr = process_remove_all_reminders(message, database)
	elif "delete!" in body:
		bldr = process_delete_comment(message, reddit, database)

	message.mark_read()

	if bldr is None:
		bldr = ["I couldn't find anything in your message."]

	bldr.extend(utils.get_footer())
	reddit.reply_message(message, ''.join(bldr))


def process_messages(reddit, database):
	for message in reddit.get_messages():
		try:
			process_message(message, reddit, database)
		except Exception as err:
			log.warning(f"Error processing message: {message.id} : {message.author.name}")
			log.warning(traceback.format_exc())
