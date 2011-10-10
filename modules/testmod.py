#Module:	testmod

#IgnoreDependencies: nothing>1.0, something

from fwee import event

def do_rehash(event, who, reason):
	pass

def init():
	event.listen('Rehash', do_rehash)

def cleanup():
	print "cleanup"
