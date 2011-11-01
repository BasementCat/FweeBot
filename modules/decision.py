#Module: decision

import re, random
from fwee import event, config, log, core, common

def init():
	event.listen('Command/DECIDE', decide)

def cleanup():
	event.unlisten(decide)

def decide(evname, net, message, args):
	message.reply("%s: %s"%(message.fromnick.split("!")[0], " ".join(args).rstrip("?").split(" or ")[random.randint(0,9999)&1]))