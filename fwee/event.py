import re, time
from fwee import log

registered_handlers		=	{}

scheduled_events={}
schedule_queue={}
next_scheduled_event=None
running=False

class EventError(Exception): pass
class EventStopError(Exception): pass

def listen(event, handler, position='last'):
	match=re.search(r"\[(.*?)\]", event)
	if match:
		match_parts=match.group(1).split(",");
		for part in match_parts:
			rangeparts=re.match(r"^(\d+)-(\d+)$", part)
			if rangeparts:
				for i in range(int(rangeparts.group(1)), int(rangeparts.group(2))+1):
					listen(re.sub(r"\[.*?\]", "%03d"%(i), event), handler, position)
			else:
				listen(re.sub(r"\[.*?\]", part, event), handler, position)
		return
	global registered_handlers
	log.edebug("Adding %s as handler for %s, position %s", handler, event, position)
	if not registered_handlers.has_key(event):
		registered_handlers[event]=[]
	if position=='first':
		registered_handlers[event].insert(0, handler)
	else:
		registered_handlers[event].append(handler)

def unlisten(handler, event=None):
	global registered_handlers
	if event is None:
		for event, handlers in registered_handlers.items():
			if handler in handlers: registered_handlers[event].remove(handler)
	else:
		if registered_handlers.has_key(event):
			if handler in registered_handlers[event]:
				registered_handlers[event].remove(handler)

def trigger(full_event, *args, **kwargs):
	global registered_handlers
	event_parts=[]
	for event_part in full_event.split('/'):
		event_parts.append(event_part)
		cur_event='/'.join(event_parts)
		if registered_handlers.has_key(cur_event):
			for handler in registered_handlers[cur_event]:
				try:
					handler(cur_event, *args, **kwargs)
				except EventStopError as e:
					return

def schedule(what, delay=None, at=None, count=None, *args, **kwargs):
	if delay is None and at is None: raise EventError("Either a delay or time must be specified!")
	global scheduled_events, schedule_queue, running
	event={'what': what, 'delay': delay, 'at': at, 'args': args, 'kwargs': kwargs, 'count': count if at is None else 1, 'runs': 0, 'lastrun': 0, 'nextrun': at if delay is None else time.time()+delay}
	if running:
		schedule_queue[str(what)]=event
		return
	else:
		scheduled_events[str(what)]=event
		reschedule()

def unschedule(what):
	global scheduled_events, next_scheduled_event
	if scheduled_events.has_key(str(what)):
		event=scheduled_events[str(what)]
		del scheduled_events[str(what)]
		if event==next_scheduled_event:
			next_scheduled_event=None
			reschedule()
		return True
	return False

def reschedule():
	global scheduled_events, next_scheduled_event, schedule_queue
	for name, ev in schedule_queue.items():
		scheduled_events[name]=ev
	schedule_queue={}
	for event in scheduled_events.values():
		if next_scheduled_event is None or event['nextrun']<next_scheduled_event['nextrun']:
			next_scheduled_event=event

def run():
	global scheduled_events, next_scheduled_event, running
	if next_scheduled_event is None: return
	if time.time()<next_scheduled_event['nextrun']: return
	running=True
	if type(next_scheduled_event['what']) is str:
		trigger(next_scheduled_event['what'], *next_scheduled_event['args'], **next_scheduled_event['kwargs'])
	else:
		next_scheduled_event['what'](*next_scheduled_event['args'], **next_scheduled_event['kwargs'])
	next_scheduled_event['runs']+=1
	next_scheduled_event['lastrun']=time.time()
	if next_scheduled_event['count'] is not None and next_scheduled_event['runs']>=next_scheduled_event['count']:
		unschedule(next_scheduled_event['what'])
	else:
		next_scheduled_event['nextrun']=next_scheduled_event['nextrun']+next_scheduled_event['delay']
	running=False
	reschedule()