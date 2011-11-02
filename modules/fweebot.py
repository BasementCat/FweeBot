#Module:	fweebot

import re
from fwee import event, config, log, core, common
from fwee.core import dfl
from fwee.networking import Channel, User

dataQueue={}

class IRCMessage(object):
	def __init__(self, command, args, **kwargs):
		self.command=command
		self.parameters=args
		self.fromnick=dfl(kwargs, 'fromnick', None)
		self.network=None
	
	@classmethod
	def parse(self, net, data):
		fromnick=None
		parameters=None
		command=None
		if data.startswith(':'):
			fromnick, data=re.split(r"\s+", data, 1)
			fromnick=fromnick[1:]
		command, data=re.split(r"\s+", data, 1)
		command=command.upper()
		params=common.pad(re.split(r"\s+:", data, 1), 2, "")
		if params[0].startswith(':'):
			parameters=[params[0][1:]]
		else:
			parameters=re.split(r"\s+", params[0])
			if len(params)>1:
				parameters.append(params[1])
		out=IRCMessage(command, parameters, fromnick=fromnick)
		out.network=net
		return out
	
	def __str__(self):
		out=[]
		if self.fromnick: out.append(":"+self.fromnick)
		out.append(self.command)
		out.extend(self.parameters)
		if len(self.parameters) and re.search(r"\s", str(self.parameters[-1])): out[-1]=":"+out[-1]
		return " ".join(out)
	
	def reply(self, message, *args):
		if self.network is None: raise Exception("Cannot reply to messages with no network")
		replyto=self.parameters[0] if self.parameters[0].startswith('#') else self.fromnick.split("!")[0]
		self.network.sendf("%s %s :%s\r\n", self.command, replyto, message%args)

def init():
	event.listen('Network/Incoming/Raw', dispatchMessages)
	event.listen('Server/Connect/Success', sendAuthentication)
	event.listen('Network/Incoming/Message/PING', respondToPing)
	event.listen('Network/Incoming/Message/[001-005]', setRegistered)
	event.listen('Server/Disconnect', handleDisconnect)
	event.listen('Server/Connect/Failure', handleDisconnect)
	event.listen('Network/Authenticated', doAutojoin)
	event.listen('Network/Incoming/Message/JOIN', handleChannelUserChange)
	event.listen('Network/Incoming/Message/353', handleChannelUserChange)
	event.listen('Network/Incoming/Message/PART', handleChannelUserChange)
	event.listen('Network/Incoming/Message/QUIT', handleChannelUserChange)
	event.listen('Network/Incoming/Message/KICK', handleChannelUserChange)
	event.listen('Network/Incoming/Message/PRIVMSG', dispatchCommands)
	event.listen('Command/XYZZY', zork)
	if core.DEBUG:
		event.listen('Network/Incoming/Message/*', printmsgs)
		event.listen('Network/Incoming/Message/366', handleChannelUserChange)

def cleanup():
	event.unlisten(dispatchMessages)
	event.unlisten(sendAuthentication)
	event.unlisten(respondToPing)
	event.unlisten(setRegistered)
	event.unlisten(handleDisconnect)
	event.unlisten(doAutojoin)
	event.unlisten(handleChannelUserChange)
	event.unlisten(dispatchCommands)
	event.unlisten(zork)

def printmsgs(evname, net, message):
	log.edebug('[%s%s] %s', '<<<', net.name, str(message))

def setRegistered(evname, net, message):
	if not net.authenticated:
		log.info("Registered with %s", net.name)
		net.authenticated=True
		if message.command=='001':
			net.nick=message.parameters[0]
		event.trigger('Network/Authenticated/'+net.name, net=net)

def respondToPing(evname, net, message):
	net.sendf("PONG %s\r\n", message.parameters[0])

def doAutojoin(evname, net):
	if net.channels:
		for channel in net.channels:
			net.sendf("JOIN %s\r\n", channel)

def handleDisconnect(evname, net, reason="Could not connect"):
	log.error("Disconnected from network %s: %s", net.name, reason)
	if net.reconnect is not None:
		log.info("%s: reconnecting in %ds", net.name, net.reconnect)
		event.schedule(net.connect, delay=net.reconnect, count=1)

def dispatchMessages(evname, net):
	global dataQueue
	data=net.recv()
	if not data:
		net.lostConnection('connection reset by peer')
		return
	if not data.endswith("\r\n"):
		if not dataQueue.has_key(net.name):
			dataQueue[net.name]=""
		dataQueue[net.name]+=data
		log.edebug("Queued %db for net %s", len(data), net.name)
		return
	if dataQueue.has_key(net.name) and dataQueue[net.name]:
		log.edebug("Unqueued %db for net %s", len(dataQueue[net.name]), net.name)
		data=dataQueue[net.name]+data
		del(dataQueue[net.name])
	data=data.strip()
	data=re.split('\r\n', data)
	for line in data:
		message=IRCMessage.parse(net, line)
		event.trigger('Network/Incoming/Message/*/'+net.name, net, message)
		event.trigger('Network/Incoming/Message/'+message.command+'/'+net.name, net, message)

def sendAuthentication(evname, net, server):
	log.info("%s: connected to %s/%s", net.name, server[0], server[1])
	passwd=config.get('Networks/'+net.name+'/Password', None)
	if passwd:
		net.sendf("PASS %s\r\n", passwd)
	net.sendf("NICK %s\r\n", config.get('Networks/'+net.name+'/Nick', core.NAME))
	net.sendf("USER %s %d * :%s\r\n",
		config.get('Networks/'+net.name+'/Ident', core.NAME),
		config.get('Networks/'+net.name+'/InitModes', 0),
		config.get('Networks/'+net.name+'/Realname', "%s v%s"%(core.NAME, core.VERSION))
		)

def handleChannelUserChange(evname, net, message):
	if message.command=='JOIN':
		chan=Channel.add(net, message.parameters[0])
		if net.isFromMe(message.fromnick):
			log.edebug("I just joined %s", message.parameters[0])
		else:
			log.info("%s: %s joined %s", net.name, message.fromnick, message.parameters[0])
			chan.addUser(message.fromnick.split("!")[0])
	elif message.command=='PART' or message.command=='QUIT':
		log.info("%s: %s left %s: %s: %s", net.name, message.fromnick, message.parameters[0], message.command, message.parameters[-1])
		chan=Channel.add(net, message.parameters[0])
		chan.removeUser(message.fromnick.split("!")[0])
	elif message.command=='KICK':
		log.info("%s: %s kicked %s from %s: %s", net.name, message.fromnick, message.parameters[1], message.parameters[0], message.parameters[-1])
		chan=Channel.add(net, message.parameters[0])
		chan.removeUser(message.parameters[1])
	elif message.command=='353':
		#2011-08-21 11:24:44 [EDEBUG ]: [<<<Local] :irc.local 353 fwee = #test :@alec fwee  [in /home/alec/Desktop/fweebot/modules/fweebot.py/printmsgs(), line 56]
		chan=Channel.add(net, message.parameters[2])
		for name in message.parameters[3].split():
			chan.addUser(name)
	elif core.DEBUG and message.command=='366':
		chan=Channel.add(net, message.parameters[1])
		#log.debug("Channel %s has %s", chan.name, ", ".join([c['status']+c['nick'] for c in chan.users.values()]))

def parseArguments(args):
	if args is None: return []
	escapedChars={'r':"\r", 'n':"\n", 't':"\t"}
	inString=False
	escape=False
	cur=''
	out=[]
	for c in args:
		if escape:
			if escapedChars.has_key(c):
				cur+=escapedChars[c]
			else:
				cur+=c
			escape=False
		elif inString:
			if c=='"':
				out.append(cur)
				cur=""
				inString=False
			else:
				cur+=c
		elif c=='\\':
			escape=True
		elif c=='"':
			if cur=="":
				inString=True
			else:
				cur+=c
		elif c in (' ', "\t"):
			if cur!="":
				out.append(cur)
				cur=""
		else:
			cur+=c
	if cur!="": out.append(cur)
	return out

def dispatchCommands(evname, net, message):
	commandchar=config.get('Networks/'+net.name+'/Channels/'+message.parameters[0]+'/CommandChar')
	if commandchar is None: commandchar=config.get('Networks/'+net.name+'/CommandChar')
	if commandchar is None: commandchar=config.get('CommandChar', '!')
	if message.parameters[-1].startswith('?trigger'):
		message.reply("This bots current trigger is "+commandchar)
		return
	#if not message.parameters[-1].startswith(commandchar): return
	match=re.match(r'^'+commandchar+r'(\S+)(?:\s+(.*))?$', message.parameters[-1])
	if not match: return
	event.trigger("Command/"+match.group(1).upper(), net=net, message=message, args=parseArguments(match.group(2)))

def zork(evname, net, message):
	message.reply("Nothing happens.")