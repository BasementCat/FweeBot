#Module: decision

import re, random
from fwee import event, config, log, core, common

def init():
	event.listen('Command/DECIDE', decide)

def cleanup():
	event.unlisten(decide)

def decide(evname, net, message, args):
	fromNick=message.fromnick.split("!")[0]
	opts=" ".join(args).rstrip("?").split(" or ")
	if len(opts)<2:
		message.reply("%s: need more options!"%(fromNick,))
	else:
		message.reply("%s: %s"%(fromNick, opts[random.randint(0,9999)&1]))