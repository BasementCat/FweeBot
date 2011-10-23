import os
import event, log, config

NAME			=	'Fweebot'
VERSION			=	'0.1.0'
CONFIGFILE		=	'fwee.conf'
CONFIGLOCATIONS	=	['./', os.path.expanduser('~/.fwee/'), '/etc/fwee/']
LOADEDCONFIG	=	None
CONNECTTIMEOUT	=	5.0
SOCKTIMEOUT		=	0.25
RECVBUF			=	1024
SELECTTIMEOUT	=	0.1
DEBUG			=	True

class ProgrammerError(Exception): pass

def rehash(who, reason, *args):
	log.info('Rehash requested by %s: %s', who, (reason%args))
	config.loadConfig()
	event.trigger('Rehash', who, reason)

def dfl(thedict, key, thedefault=None):
	return thedict[key] if thedict.has_key(key) else thedefault

def workingDir():
	if LOADEDCONFIG is None: raise ProgrammerError("workingDir() called before config is loaded!")
	return config.get('Core/WorkingDir', os.path.dirname(LOADEDCONFIG))