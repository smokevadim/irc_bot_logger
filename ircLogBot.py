# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
from os import path
from datetime import datetime
from random import choice
from threading import Thread

# variables
from vars import *

# email transport
from smtp import send_mail


total_channels = []
total_channels_flag = False
number_of_total_channels = 0
attemps = 0
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
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message.encode('utf-8')))
        self.file.flush()

    def close(self):
        self.file.close()


class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    channels = []
    write_time = datetime.now()
    all_done = False
    count = 0

    #nickname = NICKNAME
    def __init__(self, nick, channels_to_connect=[]):
        if channels_to_connect:
            self.channels = channels_to_connect
        nickname = nick

    def connectionMade(self):
        global attemps

        attemps += 1
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))
        if not self.channels:
            self.sendLine('LIST')

    def connectionLost(self, reason):
        print(reason)
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s (%s)]" %
                        (time.asctime(time.localtime(time.time())),
                         reason)
                        )
        self.logger.close()
        channels = []

    # callbacks for events
    def signedOn(self):
        global attemps
        """
        Called after successfully signing on to the server.
        """
        attemps = 0

    def kickedFrom(self, channel, kicker, message):
        """
        Called when I am kicked from a channel.
        """
        pass

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        global total_channels
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
            MessageLogger(open(path.join(CURRENT_DIR, 'logs', channel), "a")).log('{}: {}'.format(user, msg))
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

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))

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
            return
        self.count = 0
        print('Joining channels ({} left)'.format(len(self.channels)))
        # for n, channel in enumerate(channels, start=1):
        channel = []
        while True:
            if self.count == STEP_CHANNELS:
                write_time = datetime.now()
                # random_nick = 'Boko_'+''.join(choice('abcde') for _ in range(5))
                # self.setNick(random_nick)
                # random_nicks.append(random_nick)
                break
            if len(self.channels) > 0:
                # channel = channels.pop(0)
                channel.append(self.channels.pop())
                self.count += 1
                # self.join(channel)
            else:
                self.all_done = True
                break
        print('joining: {}'.format(channel))
        self.sendLine('JOIN ' + ','.join(channel))

        if self.all_done:
            # all channels are done
            print('-------JOINED--------')
            #for nick in random_nicks:
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
            line = line.decode('utf-8', 'backslashreplace')
        line = irc.lowDequote(line)

        if (self.write_time) and len(self.channels) > 0:
            delta = datetime.now() - self.write_time
            if int(delta.total_seconds()) > 5:
                self.join_channels()

        try:
            prefix, command, params = irc.parsemsg(line)

            # too many channels
            # if '405' in command:
            #     if 'You have joined too many channels' in params[2]:
            #        print('Total channels before restrict: ' + str(joined_channels))

            # skip not interesting messages
            if ('372' and '332' and '353' and '322' and 'PRIVMSG' and 'QUIT') not in str(command):
                print('prefix: {}, command: {}, params: {}'.format(prefix, command, params))

            # total joined channels
            if '319' in command:
                joined_channels += params[2]
            if '318' in command:
                if 'End of /WHOIS list.' in params:
                    self.logger.log('Total joined channels: {} of all {}'.format(
                        len(joined_channels.split(' ')),
                        str(number_of_total_channels)
                    ))

            # total channels on server
            if '322' in command:  # params[1] - channel name, params[2] - number of users
                # print(command)
                if int(params[2]) >= MINIMUM_USERS:
                    #self.channels.append(params[1])
                    total_channels.append(params[1])
            if 'End of /LIST' in params:
                #total_channels = self.channels.copy()
                number_of_total_channels = len(total_channels)
                total_channels_flag = True
                self.join_channels()

            if command in irc.numeric_to_symbolic:
                command = irc.numeric_to_symbolic[command]
            else:
                self.handleCommand(command, prefix, params)

        except irc.IRCBadMessage:
            print(line)
            self.badMessage(line, *sys.exc_info())


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, filename, nick, channels_to_connect=[]):
        self.filename = filename
        self.channels_to_connect = channels_to_connect
        self.nickname = nick

    def buildProtocol(self, addr):
        p = LogBot(self.nickname, self.channels_to_connect)
        p.username = USER_NAME if USER_NAME else None
        p.password = PASSWORD if PASSWORD else None
        p.nickname = self.nickname
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        if attemps > ATTEMPS_TO_RECONNECT:
            send_mail('Maximum of attemps is reached', reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("connection failed:", reason)
        send_mail("connection failed:", reason)
        reactor.stop()


def run_instance(nick, channels=[]):
    f = LogBotFactory('main.log', nick, channels)
    reactor.connectTCP("irc.freenode.net", 6667, f)
    reactor.run()


class RunInThread(Thread):
    """
    Run bots in threads
    """

    def __init__(self, name, nick, channels = []):
        Thread.__init__(self)
        self.name = name
        self.channels = channels
        self.nick = nick

    def run(self):
        run_instance(self.nick, self.channels)
        msg = "%s is running" % self.name
        print(msg)


def get_random_nick():
    random_nick = 'Boko_'+''.join(choice('abcde') for _ in range(5))
    random_nicks.append(random_nick)
    return random_nick


if __name__ == '__main__':
    # initialize logging
    # log.startLogging(sys.stdout)

    # create factory protocol and application
    # f = LogBotFactory(sys.argv[1], sys.argv[2])
    first_thread = RunInThread('first',NICKNAME)
    first_thread.start()

    while True:
        iterate = 0
        if total_channels_flag:
            channels = []
            for n, ch in enumerate(total_channels, start=1):
                channels.append(ch)
                if n % 20 == 0:
                    iterate += 1
                    RunInThread(str(iterate), get_random_nick(), channels).start()
                    time.sleep(1)
                    channels.clear()
            break
        time.sleep(3)
