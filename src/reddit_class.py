import logging.handlers
import praw
import configparser
import traceback

import static

log = logging.getLogger("bot")


class Reddit:
	def __init__(self, user, no_post, shallow=False):
		self.no_post = no_post
		if not shallow:
			try:
				self.reddit = praw.Reddit(
					user,
					user_agent=static.USER_AGENT)
			except configparser.NoSectionError:
				log.error("User "+user+" not in praw.ini, aborting")
				raise ValueError
			static.ACCOUNT_NAME = self.reddit.user.me().name
			log.info("Logged into reddit as /u/" + static.ACCOUNT_NAME)
		else:
			static.ACCOUNT_NAME = user

	def get_messages(self):
		return self.reddit.inbox.unread(limit=500)

	def reply_message(self, message, body):
		if self.no_post:
			log.info(body)
		else:
			message.reply(body)

	def get_comment(self, comment_id):