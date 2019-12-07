# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
from os import path
from datetime import datetime

#variables
from vars import *

channels = []
total_channels = []
count = 0
write_time = False
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

    nickname = NICKNAME

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))
        self.sendLine('list')

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

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        global count, write_time, channels, total_channels
        self.logger.log("[I have joined %s]" % channel)
        count -= 1
        delta = datetime.now() - write_time
        if (count == 0) or (int(delta.total_seconds()) > 5):
            if len(channels) > 0:
                self.join_channels()
        if channel in total_channels:
            total_channels.remove(channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        print(channel,msg)
        user = user.split('!', 1)[0]
        try:
            MessageLogger(open(path.join(CURRENT_DIR, 'logs', channel), "a")).log('{}: {}'.format(user, msg))
        except Exception as e:
            print(e,user,channel,msg)
        self.logger.log("<%s> %s" % (user, msg))

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
        global count, write_time
        count = 0
        print('Joining channels ({} left)'.format(len(channels)))
        #for n, channel in enumerate(channels, start=1):
        while True:
            if count == STEP_CHANNELS:
                write_time = datetime.now()
                break
            if len(channels) > 0:
                channel = channels.pop(0)
                count += 1
                #print('{}. joining: {}'.format(count, channel))
                #print('{}. joining: {}'.format(n, channel))
                self.join(channel)
            else:
                for _ in total_channels:
                    print('Cant join in: {}'.format(_))
                print('-------JOINED--------')
                break
            # if n%10 == 0:
            #     self.clearLineBuffer()
            #     time.sleep(3)
            # if n == 100:
            #     return

    def lineReceived(self, line):
        global write_time, channels, total_channels
        if bytes != str and isinstance(line, bytes):
            # decode bytes from transport to unicode
            line = line.decode('utf-8','backslashreplace')
        line = irc.lowDequote(line)

        if (write_time) and len(channels) > 0:
            delta = datetime.now() - write_time
            if int(delta.total_seconds()) > 5:
                self.join_channels()

        try:
            prefix, command, params = irc.parsemsg(line)
            if command in irc.numeric_to_symbolic:
                command = irc.numeric_to_symbolic[command]
            if command == 'RPL_LIST': # param[1] - channel name, param[2] - number of users
                #print(command)
                if int(params[2])>= MINIMUM_USERS:
                    channels.append(params[1])
            if 'End of /LIST' in params:
                total_channels = channels
                self.join_channels()

            else:
                 self.handleCommand(command, prefix, params)
        except irc.IRCBadMessage:
            print(line)
            self.badMessage(line, *sys.exc_info())


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, filename):

        self.filename = filename

    def buildProtocol(self, addr):
        p = LogBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print
        "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)

    # create factory protocol and application
    #f = LogBotFactory(sys.argv[1], sys.argv[2])
    f = LogBotFactory('main.log')
    # connect factory to this host and port
    reactor.connectTCP("irc.freenode.net", 6667, f)

    # run bot
    reactor.run()

