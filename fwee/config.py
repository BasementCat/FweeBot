import json

config_data={}

def load(filename):
	global config_data
	fh=open(filename, 'r')
	config_json=fh.read()
	if not config_json.startswith("{"): config_json="{"+config_json+"}"
	config_data=json.loads(config_json)
	fh.close()

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
