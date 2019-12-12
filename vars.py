SERVER_NAME = 'irc.cyberarmy.com' # IRC server
PORT = 6667
NICKNAME = 'rubik'		# nickname
USER_NAME = 'rubik'	# registered username to IRC server
PASSWORD = 'smokevadim'			# password to IRC server
MINIMUM_USERS = 10		# connect to channels with minimum users
MAXIMUM_USERS = 20		# connect to channels with maximum users
ATTEMPS_TO_RECONNECT = 5 	# attemps to try reconnect on one bot
STEP_JOIN_ONE_TIME_CHANNELS = 20# number of one time channels subcribe (server not alowed more than 10)
MAXIMUM_BOTS = 4       	# maximum bots
MAXIMUM_CHANNELS_IN_ONE_BOT = 20
FULL_LOG = 1                	# 1 - display all messages, 0 if not (only errors)

### for email notification
### if use gmail.com need to enable this option on https://myaccount.google.com/lesssecureapps
ADDR_FROM = 'smoke.kaliningrad@gmail.com' # email sender
ADDR_TO = '' # email receiver
EMAIL_PASSWORD = '' # password to email server
EMAIL_SERVER = 'smtp.gmail.com'  # smtp server
