import json
import core, log

config_data={}

class ConfigError(Exception): pass

def loadConfig():
	for location in core.CONFIGLOCATIONS:
		try:
			cfgfile=location+core.CONFIGFILE
			log.edebug("Attempting to load config from %s", cfgfile)
			loadFile(cfgfile)
			return
		except IOError as e:
			log.edebug("Failed! %s", str(e))
	raise ConfigError("Failed to load any valid config files!")

def loadFile(filename):
	global config_data
	fh=open(filename, 'r')
	config_json=fh.read()
	if not config_json.startswith("{"): config_json="{"+config_json+"}"
	config_data=json.loads(config_json)
	fh.close()
	core.LOADEDCONFIG=filename

def get(full_key, default=None):
	global config_data
	curconfig=config_data
	for key in full_key.strip().strip('/').split('/'):
		if type(curconfig) is dict:
			if curconfig.has_key(key):
				curconfig=curconfig[key]
			else:
				return default
		else:
			try:
				if curconfig[int(key)]:
					curconfig=curconfig[int(key)]
				else:
					return default
			except ValueError:
				return default
	return curconfig
