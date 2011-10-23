#Module: dice

import re, random
from fwee import event, config, log, core, common

def init():
	event.listen('Command/DICE', rollDice)

def cleanup():
	event.unlisten(rollDice)

def rollDice(evname, net, message, args):
	count, sides=(1, 6)
	if len(args)>1:
		count, sides=args
	elif len(args)==1:
		dice=args[0].split("d")
		if len(dice)>1:
			count, sides=dice
		else:
			count=args[0]
			sides=6
	
	try:
		count, sides=[int(i) for i in (count, sides)]
	except ValueError:
		message.reply("Only numbers, please!")
		return
	
	log.edebug("Rolling %d dice, %d sides", count, sides)
	
	dice=[str(random.randint(1, sides)) for nothing in range(0, count)]
	dicetype="%dd%d"%(count, sides)
	who=message.fromnick.split("!")[0]+" rolls" if message.parameters[0].startswith("#") else "You roll"
	message.reply("%s %s for %s", who, dicetype, ", ".join(dice))