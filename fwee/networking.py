import socket, select, re
import log, event, core, config

networklist	=	{}
socketlist	=	{}
sockets		=	[]

class NetworkError(Exception): pass

def handleRehash(*args, **kwargs):
	global networklist
	[net.disconnect() for net in networklist.values()]
	networklist={}
	for netname, netdata in config.get('Networks', {}).items():
		networklist[netname]=Network(netname, core.dfl(netdata, 'Servers', []), core.dfl(netdata, 'Channels', []), core.dfl(netdata, 'Reconnect', 15))
		networklist[netname].connect()

def refresh():
	global socketlist, sockets
	in_list=sockets[:]
	in_ready, out_ready, except_ready=select.select(in_list, [], [], core.SELECTTIMEOUT)
	for sock in in_ready:
		net=socketlist[str(sock)]
		event.trigger('Network/Incoming/Raw/'+net.name, net)

class User(object):
	users={}
	
	def __init__(self, net, nick):
		self.network=net
		self.nick=nick
		self.channels={}
		self.channelstatus={}
		#self.users[nick.lower()]=self
	
	@classmethod
	def add(self, net, nick):
		if self.users.has_key(net.name):
			if self.users[net.name].has_key(nick.lower):
				return self.users[net.name][nick.lower]
		else:
			self.users[net.name]={}
		u=User(net, nick)
		self.users[net.name][nick.lower()]=u
		return u
	
	def setStatus(self, channel, status):
		cs=self.channelstatus[channel.name.lower()] if status[0] in ('+', '-') and self.channelstatus.has_key(channel.name.lower()) else []
		add=True
		for mode in status:
			if mode in ('+', '-'):
				add=True if mode=='+' else False
			else:
				if add:
					cs.append(mode)
				else:
					try:
						while True:
							cs.remove(mode)
					except Exception: pass
		self.channelstatus[channel.name.lower()]=cs
	
	def setStatusChar(self, channel, statuschar):
		#channel must be a channel object
		if statuschar not in ('+', '%', '@', '&', '~'): return
		self.setStatus(channel, {'+':'v', '%':'h', '@':'o', '&':'ao', '~':'qo'}[statuschar])
	
	def joinTo(self, channel):
		#channel must be a channel object
		if not self.channels.has_key(channel.name.lower()):
			self.channels[channel.name.lower()]=channel
	
	def leaveChannel(self, channel):
		if self.channels.has_key(channel.name.lower()):
			del(self.channels[channel.name.lower()])
		if self.channelstatus.has_key(channel.name.lower()):
			del(self.channelstatus[channel.name.lower()])
		if len(self.channels)==0:
			log.debug("%s: No longer tracking user %s", self.network.name, self.nick)
			del(self.users[self.network.name][self.nick.lower])

class Channel(object):
	channels={}

	def __init__(self, net, name):
		self.network=net
		self.name=name
		self.users={}
		self.topic=None
		self.modes=None
	
	@classmethod
	def add(self, net, name):
		name=name.lower()
		if self.channels.has_key(net.name):
			if self.channels[net.name].has_key(name):
				return self.channels[net.name][name]
		else:
			self.channels[net.name]={}
		chan=Channel(net, name)
		self.channels[net.name][name]=chan
		return chan
	
	def addUser(self, name):
		match=re.match(r"^([~&@%\+]?)(.*)$", name)
		u=User.add(self.network, match.group(2))
		u.joinTo(self)
		u.setStatusChar(self, match.group(1))
		if not self.users.has_key(u.nick.lower()): self.users[u.nick.lower()]=u

	def removeUser(self, name):
		if self.users.has_key(name.lower):
			u=self.users[name.lower]
			del(self.users[name.lower])
			u.leaveChannel(self)

class Network(object):
	def __init__(self, name, servers, channels=[], reconnect=15):
		self.name=name
		#self.servers=[svr.append(6667) if len(svr)<2 else svr for svr in [svr.split('/') for svr in servers]]
		self.servers=[]
		for server_s in servers:
			server_l=server_s.split('/')
			self.servers.append((server_l[0], int(server_l[1]) if len(server_l)>1 else 6667))
		self.activeserver=0
		self.channels=channels
		self.sock=None
		self.authenticated=False
		self.features={}
		self.reconnect=reconnect
		self.nick=None
	
	def isFromMe(self, messageFrom):
		match=re.match(r"^([^!]+)![^@]+@.+$", messageFrom)
		if match:
			return match.group(1)==self.nick
		else:
			return messageFrom==self.nick
	
	def connect(self):
		self.disconnect()
		for i in range(0, len(self.servers)):
			self.activeserver=i
			try:
				self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.sock.settimeout(core.CONNECTTIMEOUT)
				self.sock.connect(self.servers[self.activeserver])
				self.sock.settimeout(core.SOCKTIMEOUT)
				break
			except socket.error as e:
				log.warning('%s: Can\'t connect to %s/%d: %s', self.name, self.servers[self.activeserver][0], self.servers[self.activeserver][1], str(e))
				event.trigger('Server/Connect/Error/'+self.name, self, e, self.servers[self.activeserver])
				self.disconnect()
		if self.sock is None:
			log.error('%s: Can\'t connect to any servers!', self.name)
			event.trigger('Server/Connect/Failure/'+self.name, self)
			return False
		global socketlist, sockets
		socketlist[str(self.sock)]=self
		sockets.append(self.sock)
		event.trigger('Server/Connect/Success/'+self.name, self, self.servers[self.activeserver])
		return True
	
	def disconnect(self):
		if self.sock is not None:
			try:
				global socketlist, sockets
				if socketlist.has_key(str(self.sock)): del(socketlist[str(self.sock)])
				if self.sock in sockets: sockets.remove(self.sock)
				self.sock.close()
			except socket.error as e:
				log.warning('%s: Non-fatal error closing connection to %s/%d: %s', self.name, self.servers[self.activeserver][0], self.servers[self.activeserver][1], str(e))
			self.sock=None
		self.authenticated=False
		self.features={}
	
	def lostConnection(self, reason):
		log.edebug("%s: Lost connection: %s", self.name, reason)
		event.trigger('Server/Disconnect/'+self.name, net=self, reason=reason)
		self.disconnect()
	
	def send(self, data):
		if self.sock is None: return False
		log.edebug("[>>>%s] %s", self.name, data.strip())
		return self.sock.send(data)
	
	def sendf(self, message, *args):
		return self.send(message%args)
	
	def recv(self):
		if self.sock is None: return False
		return self.sock.recv(core.RECVBUF)