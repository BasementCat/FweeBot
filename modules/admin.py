#Module: admin

import sys
from fwee import event, config, log, core, common, networking
from fweebot import IRCMessage

def init():
	event.listen('Command/QUIT', doQuit)

def cleanup():
	event.unlisten(doQuit)

def doQuit(evname, net, message, args):
	text="Requested by %s"%(message.fromnick.split("!")[0],)
	if len(args):
		text+=": "+args[0]
	for netw in networking.networklist.values():
		netw.send(str(IRCMessage("quit", [text])))
		netw.disconnect()
	sys.exit(0)