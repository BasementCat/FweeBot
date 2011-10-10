import traceback, time

EDEBUG	=	1
DEBUG	=	2
INFO	=	4
WARNING	=	8
ERROR	=	16

level_text={	1:	'EDEBUG',
				2:	'DEBUG',
				4:	'INFO',
				8:	'WARNING',
				16:	'ERROR'
			}

def leveltext(level, pad=False):
	text=level_text[level] if level_text.has_key(level) else '???'
	padding=''
	if pad: padding=' '*(7-len(text))
	return text+padding

def logf(level, message, *args, **kwargs):
	final_message=message%args
	level_text=leveltext(level, True)
	stack_offset=-2
	if kwargs.has_key('stack_offset'): stack_offset-=kwargs['stack_offset']
	calling_file, calling_line, calling_function, call=traceback.extract_stack()[stack_offset]
	print "%s [%s]: %s [in %s/%s(), line %d]"%(
		time.strftime('%Y-%m-%d %H:%M:%S'),
		level_text,
		final_message,
		calling_file,
		calling_function,
		calling_line
		)

def edebug(message, *args): return logf(EDEBUG, message, *args, stack_offset=1)
def debug(message, *args): return logf(DEBUG, message, *args, stack_offset=1)
def info(message, *args): return logf(INFO, message, *args, stack_offset=1)
def warning(message, *args): return logf(WARNING, message, *args, stack_offset=1)
def error(message, *args): return logf(ERROR, message, *args, stack_offset=1)
