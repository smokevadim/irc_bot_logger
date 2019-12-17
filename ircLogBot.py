# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
from os import path, makedirs
from datetime import datetime
from random import choice
from threading import Thread
import base64

# variables
from vars import *

# email transport
from smtp import send_mail


total_channels = []
total_channels_flag = False
number_of_total_channels = 0
random_nicks = []
random_nicks.append(NICKNAME)

joined_channels = ''

CURRENT_DIR = path.dirname(path.realpath(__file__))


class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """

    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        print(message)
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message.encode('utf-8')))
        self.file.flush()

    def close(self):
        self.file.close()


class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    channels = []
    bot_channels = []
    write_time = datetime.now()
    bot_signed = False

    all_done = False
    count = 0
    identified = False

    def __init__(self, nick, channels_to_connect=[]):
        print('Initializing bot ' + self.nickname)
        if channels_to_connect:
            self.channels = channels_to_connect.copy()
            self.bot_channels = channels_to_connect[:]
        nickname = nick
        self.attemps = 0

    def register(self, nickname, hostname='foo', servername='bar'):
        """
        Login to the server.

        @type nickname: C{str}
        @param nickname: The nickname to register.
        @type hostname: C{str}
        @param hostname: If specified, the hostname to logon as.
        @type servername: C{str}
        @param servername: If specified, the servername to logon as.
        """
        # FREENODE NEED SASL AUTH
        if 'freenode' in SERVER_NAME.lower():
            #self.auth_with_SASL()
            self.sendLine('CAP LS')
            print('CAP LS')
            #return

        # for quakenet
        if 'quakenet' in SERVER_NAME:
            self.sendLine('auth {} {}'.format(USER_NAME, PASSWORD))

        if self.password is not None:
            self.sendLine("PASS %s" % self.password)
        self.setNick(nickname)
        if self.username is None:
            self.username = nickname
        self.sendLine("USER %s %s %s :%s" % (self.username, hostname, servername, self.realname))
        print('Sending USER %s %s %s :%s' % (self.username, hostname, servername, self.realname))


    def connectionMade(self):
        self.attemps = 0
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))

    def auth_with_SASL(self):
        #self.sendLine('AUTHENTICATE PLAIN')

        #print('CAP REQ :sasl')
        creds = '{username}\0{username}\0{password}'.format(
            username=self.username,
            password=self.password)
        to_send = 'AUTHENTICATE {}'.format(base64.b64encode(creds.encode('utf8')).decode('utf8'))
        self.sendLine(to_send)
        print(to_send)
        self.sendLine('CAP END')
        print('CAP END')
        #print('Authenticating with SASL: ' + to_send)

    def make_identify(self):
        s = 'IDENTIFY {} {}'.format(NICKNAME, PASSWORD)
        print(s)
        self.msg('NickServ', s)

    def connectionLost(self, reason):
        print(reason)
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[%s: disconnected at %s (%s) (attemps: %s)]" %
                        (self.nickname,
                        time.asctime(time.localtime(time.time())),
                        reason,
                        self.attemps
                        ))

        self.logger.close()

        channels = []

        ### send email if attemps to connect more than in vars.py
        self.attemps += 1
        if (self.attemps > ATTEMPS_TO_RECONNECT) and not self.already_send_mail_flag:
            send_mail('Maximum of attemps is reached', str(reason))
            self.already_send_mail_flag = True
            reactor.stop

    # callbacks for events
    def signedOn(self):
        """
        Called after successfully signing on to the server.
        """
        self.attemps = 0
        self.bot_signed = True
        print('Bot %s signed' % self.nickname)

        ### others bots
        if self.channels:
            self.logger.log("[{}: connected at {}, have {} channels to join]".format(
                self.nickname,
                time.asctime(time.localtime(time.time())),
                len(self.channels)
            ))

            ### trying to register nickname
            # s = 'msg NickServ REGISTER {} {}'.format(PASSWORD, REGISTERED_EMAIL)
            if self.password:
                self.make_identify()
            # self.sendLine(s)

        ### first bot
        else:
            self.logger.log("[{} (FIRST BOT): connected at {}]".format(
                self.nickname,
                time.asctime(time.localtime(time.time())),
            ))

            ### asking server for all channels
            self.sendLine('LIST')

    def kickedFrom(self, channel, kicker, message):
        """
        Called when I am kicked from a channel.
        """
        print('Bot %s kicked from %s' % (self.nickname, channel))
        pass

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)
        self.count -= 1
        delta = datetime.now() - self.write_time
        if (self.count == 0) or (int(delta.total_seconds()) > 5):
            if len(self.channels) > 0:
                self.join_channels()
        # if channel in total_channels:
        #     total_channels.remove(channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        # print(channel, msg)
        user = user.split('!', 1)[0]
        try:
            logs_directory = path.join(CURRENT_DIR, 'logs')
            if not path.exists(logs_directory):
                makedirs(logs_directory)
            MessageLogger(open(path.join(logs_directory, channel), "a")).log('{}: {}'.format(user, msg))
        except Exception as e:
            print(e, user, channel, msg)
        # self.logger.log("<%s> %s" % (user, msg))

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "Sorry mate, i can\'t answer you"
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            # msg = "%s: " % user
            # self.msg(channel, msg)
            self.logger.log("<%s> %s" % (self.nickname, msg))

    # def action(self, user, channel, msg):
    #     """This will get called when the bot sees someone do an action."""
    #     user = user.split('!', 1)[0]
    #     self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    # def irc_NICK(self, prefix, params):
    #     """Called when an IRC user changes their nickname."""
    #     old_nick = prefix.split('!')[0]
    #     new_nick = params[0]
    #     self.logger.log("%s is now known as %s" % (old_nick, new_nick))

    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'

    def join_channels(self):
        global random_nicks
        if not total_channels:
            print('%s: no total channels to join' % self.nickname)
            return
        if (not self.identified) and PASSWORD:
            print('Bot %s not identified' % self.nickname)
            return
        if not self.bot_signed:
            return
        self.count = 0
        print('Joining channels ({} left)'.format(len(self.channels)))
        # for n, channel in enumerate(channels, start=1):
        channel = []
        while True:
            if self.count == STEP_JOIN_ONE_TIME_CHANNELS:
                write_time = datetime.now()
                # random_nick = 'Boko_'+''.join(choice('abcde') for _ in range(5))
                # self.setNick(random_nick)
                # random_nicks.append(random_nick)
                break
            if len(self.channels) > 0:
                # channel = channels.pop(0)
                channel_to_join = self.channels.pop()
                if channel_to_join not in joined_channels:
                    channel.append(channel_to_join)
                self.count += 1
                # self.join(channel)
            else:
                self.all_done = True
                break
        print('joining: {}'.format(channel))
        self.sendLine('JOIN ' + ','.join(channel))

        if self.all_done or len(self.channels) == 0:
            # all channels are done
            print('-------JOINED--------')
            # for nick in random_nicks:
            self.sendLine('WHOIS ' + self.nickname)

        # if n%10 == 0:
        #     self.clearLineBuffer()
        #     time.sleep(3)
        # if n == 100:
        #     return

    def lineReceived(self, line):
        global total_channels, joined_channels, number_of_total_channels, total_channels_flag
        if bytes != str and isinstance(line, bytes):
            # decode bytes from transport to unicode
            #line = line.decode('utf-8', 'backslashreplace')
            line = line.decode('utf-8', 'ignore')
        line = irc.lowDequote(line)

        try:
            prefix, command, params = irc.parsemsg(line)
            all_params = ''.join([p for p in params]).lower()
            # too many channels
            # if '405' in command:
            #     if 'You have joined too many channels' in params[2]:
            #        print('Total channels before restrict: ' + str(joined_channels))

            ### skip not interesting messages
            # to_skip = set(['372', '332', '353', '322', 'PRIVMSG', 'QUIT'])
            # to_skip = set(['353', '322', 'PRIVMSG'])
            to_skip = set([''])
            if (command not in to_skip) or (FULL_LOG == 1):
                print('prefix: {}, command: {}, params: {}'.format(prefix, command, params))

            ### SASL auth if requiered
            if 'CAP' in command:
                print('CAP')
                if 'ack' in all_params:
                    self.sendLine('AUTHENTICATE PLAIN')
                    print('AUTHENTICATE PLAIN')
                if 'ls' in all_params:
                    print('ls')
                    if 'sasl' in all_params:
                        print('sasl')
                        self.sendLine('CAP REQ :sasl')
                        print('CAP REQ :sasl')
            if 'AUTHENTICATE' in command:
                if '+' in params[0]:
                    self.auth_with_SASL()
            if '903' in command:
                self.identified = True

            ### ERROR
            if 'error' in command.lower():
                if 'too fast' in params[0]:
                    self.logger.log('[{}: An error occured: {}]'.format(
                        self.nickname,
                        params[0]
                    ))
                    time.sleep(10)
            if '4' in str(command)[0]:
                self.logger.log('[{}: An error occured: {}]'.format(
                    self.nickname,
                    ' '.join([s for s in params])
                ))

            ### 353: users in channel
            # if '353' in command:
            #     if self.nickname in params[3]:
            #         self.joined(params[2])
            #         return

            ### 433: Nickname is already in use
            if '433' in command:
                self.setNick(get_random_nick())

            ### irc.cyberarmy.net need to pause 60 sec to request /LIST
            if 'you cannot list within the first' in ''.join([p for p in params]).lower():
                time.sleep(60)
                self.sendLine('LIST')

            ### total joined channels
            if '319' in command:
                joined_channels += params[2]
            if '318' in command:
                self.logger.log('[{}: joined channels at this time: {} of all {}]'.format(
                    self.nickname,
                    len(joined_channels.split(' '))-1,
                    number_of_total_channels
                ))

            ### signed on server
            signed_commands = ['903', '376', '422']
            if command in signed_commands:
                self.signedOn()
                return

            #### total channels on server
            if '322' in command:  # params[1] - channel name, params[2] - number of users
                # print(command)
                try:
                    if int(params[-2]) >= MINIMUM_USERS:
                        if MAXIMUM_USERS:
                            if int(params[-2]) <= MAXIMUM_USERS:
                                total_channels.append(params[1])
                        else:
                            total_channels.append(params[1])
                except:
                    print ('Channel %s have unformatted number of users' % params[1])
            # if 'End of /LIST' in params:
            if '323' in command:
                # total_channels = self.channels.copy()
                number_of_total_channels = len(total_channels)
                total_channels_flag = True
                self.logger.log('[Summary channels to join: {}]'.format(len(total_channels)))

            if command in irc.numeric_to_symbolic:
                command = irc.numeric_to_symbolic[command]
            else:
                self.handleCommand(command, prefix, params)

            ### Identifiend
            identified_list = ['You are now logged', 'You are now identified', 'There are already', 'No such nick']
            if (len(params) > 0) and (self.nickname == params[0]):
                for i in identified_list:
                    if i.lower() in all_params:
                        ### Server may have limit for nick identified in one account
                        ### and we need to try to get all others channels without make identified
                        self.identified = True

            ### joining channels
            if self.write_time and len(self.channels) > 0:
                delta = datetime.now() - self.write_time
                if int(delta.total_seconds()) > 5:
                    self.join_channels()


        except irc.IRCBadMessage:
            print(line)
            self.badMessage(line, *sys.exc_info())


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, filename, nick, channels_to_connect=[]):
        print('Initializing LogBotFactory for ' + nick)
        self.filename = filename
        self.channels_to_connect = channels_to_connect
        self.nickname = nick
        self.already_send_mail_flag = False
        self.attemps = 0

    def buildProtocol(self, addr):
        print('Building protocol for %s' % self.nickname)
        p = LogBot(self.nickname, self.channels_to_connect)
        p.username = USER_NAME if USER_NAME else self.nickname
        p.password = PASSWORD if PASSWORD else None
        p.nickname = self.nickname
        p.factory = self
        p.already_send_mail_flag = self.already_send_mail_flag
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        self.attemps += 1
        if (self.attemps > ATTEMPS_TO_RECONNECT) and not self.already_send_mail_flag:
            send_mail("connection failed:", str(reason))
            self.already_send_mail_flag = True
        else:
            connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("connection failed:", reason)
        if not self.already_send_mail_flag:
            send_mail("connection failed:", str(reason))
            self.already_send_mail_flag = True
        reactor.stop()


def run_instance(nick, channels=[]):
    try:
        f = LogBotFactory('main.log', nick, channels)
        #reactor.connectTCP(SERVER_NAME, PORT, f)
        reactor.callLater(4, reactor.connectTCP, SERVER_NAME, PORT, f)
        reactor.run()
    except Exception as e:
        pass
        #print('Error when running: %s' % e)


class RunInThread(Thread):
    """
    Run bots in threads
    """

    def __init__(self, name, nick, channels=[]):
        Thread.__init__(self, target=reactor.run, args=(False,))
        self.name = name
        self.channels = channels
        self.nick = nick

    def run(self):
        run_instance(self.nick, self.channels)
        msg = "%s is running" % self.name
        print(msg)


def get_random_nick():
    random_nick = 'B_' + ''.join(choice('abcdefgh') for _ in range(7))
    random_nicks.append(random_nick)
    return random_nick


def check_manual_channels():
    global total_channels, total_channels_flag, number_of_total_channels
    channels_file = path.join(CURRENT_DIR, 'channels.txt')
    if path.exists(channels_file):
        with open(channels_file, 'r') as f:
            total_channels = [row.strip() for row in f]
            if len(total_channels) > 0:
                total_channels_flag = True
                number_of_total_channels = len(total_channels)


if __name__ == '__main__':
    check_manual_channels()
    # initialize logging
    # log.startLogging(sys.stdout)

    # create factory protocol and application
    # f = LogBotFactory(sys.argv[1], sys.argv[2])
    if not total_channels_flag:
        first_thread = RunInThread('first', NICKNAME)
        first_thread.start()

    while True:
        iterate = 0
        if total_channels_flag:
            channels = []
            for n, ch in enumerate(total_channels, start=1):
                if iterate == MAXIMUM_BOTS:  # maximum allowed bots
                    break
                channels.append(ch)
                if (n % MAXIMUM_CHANNELS_IN_ONE_BOT == 0) or (n == len(total_channels)):
                    iterate += 1
                    thread = RunInThread(str(iterate), get_random_nick(), channels[:])
                    thread.start()
                    channels.clear()
                    if n == len(total_channels):
                        break
                    time.sleep(60)
            print('-------------ALL BOTS (%s) RUNNING-------------' % iterate)
            break
        time.sleep(3)  # 3
