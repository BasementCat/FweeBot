import glob, re, sys
import log

loaded_modules		=	{}
available_modules	=	{}

class ModuleError(Exception):
	"""Represents an error occurring during the loading or unloading of modules."""
	pass

class LoadableModule(object):
	def __init__(self, **kwargs):
		if not kwargs.has_key('Module'): raise ModuleError("Module header is invalid - the Module: line is not present")
		self.Version=0x00000000
		if kwargs.has_key('Version') and str(kwargs['Version']).find('.')>=0: kwargs['Version']=self.parseVersionString(kwargs['Version'])
		#print kwargs
		if kwargs.has_key('Dependencies'):
			newdeps={}
			for dep in kwargs['Dependencies'].split(','):
				dep=dep.strip()
				m=re.match("^(.*?)(([<>=! ]{1,2})(.*))?$", dep)
				#if not m: raise ModuleError("Epic fail in dep: %s"%dep)
				depmod, nothing, ver_rel, ver=m.groups()
				if ver_rel is not None:
					if not ver_rel.strip(): ver_rel='='
				newdeps[depmod]={'Module':depmod, 'Version':ver, 'VersionRelationship':ver_rel}
			kwargs['Dependencies']=newdeps
		self.__dict__.update(kwargs)
	
	def __str__(self):
		return "%s v%s"%(self.Module, self.versionString())
	
	def checkDependencies(self):
		if not self.__dict__.has_key('Dependencies'): return True
		global loaded_modules
		unsatisfied=[]
		for dep in self.Dependencies.values():
			if not loaded_modules.has_key(dep['Module']):
				unsatisfied.append(dep)
				continue
			
			if dep.has_key('Version') and dep['Version'] is not None:
				if not eval(loaded_modules[dep['Module']].Version+dep['VersionRelationship']+self.parseVersionString(dep['Version'])):
					unsatisfied.append(dep)
					continue
		
		if unsatisfied:
			e=ModuleError("Module %s has unsatisfied dependencies"%(self.Module))
			e.unsatisfied=unsatisfied
			raise e
		
		return True
	
	def versionString(self):
		return ".".join((
			str( (self.Version>>24)&0x000000ff),
			str( (self.Version>>16)&0x000000ff),
			str( (self.Version>>8 )&0x000000ff),
			str(  self.Version     &0x000000ff)
			))
	
	@classmethod
	def parseVersionString(self, vstr):
		vint=0x00000000
		position=24
		parts=vstr.split('.')
		while len(parts)<4: parts.append('0')
		for part in parts:
			vint=vint|((int(part)&0x000000ff)<<position)
			position=position-8
		return vint

def get(modname):
	global loaded_modules
	if not loaded_modules.has_key(modname): raise ModuleError("Module %s is not loaded"%modname)
	return loaded_modules[modname].ModuleObject

def load(modname):
	global loaded_modules, available_modules
	if loaded_modules.has_key(modname):
		mod=loaded_modules[modname]
		raise ModuleError("%s is already loaded"%str(mod))
	elif not available_modules.has_key(modname):
		raise ModuleError("Module %s doesn't seem to exist (did you refresh the module list?)"%modname)
	
	module_data=available_modules[modname]
	try:
		module_data.checkDependencies()
	except ModuleError as e:
		depstring=[]
		for dep in e.unsatisfied:
			depstring.append("%s%s%s"%(dep['Module'], dep['VersionRelationship'] if dep['VersionRelationship'] is not None else '', dep['Version'] if dep['Version'] is not None else ''))
		depstring=", ".join(depstring)
		ne=ModuleError("Module %s cannot be loaded: requires: %s"%(module_data.Module, depstring))
		ne.unsatisfied=e.unsatisfied
		raise ne
	
	try:
		module_obj=__import__(module_data.ModuleLogicalPath)
		module_obj=sys.modules[module_data.ModuleLogicalPath]
		module_obj.init
		module_obj.cleanup
	except Exception as e:
		forciblyUnload(module_data)
		raise ModuleError("Module %s cannot be loaded: %s"%(modname, str(e)))
	
	try:
		module_obj.init()
	except Exception as e:
		forciblyUnload(module_data)
		raise ModuleError("Module %s did not initialize properly! %s"%(modname, str(e)))
	
	module_data.ModuleObject=module_obj
	loaded_modules[modname]=module_data
	del(available_modules[modname])

def forciblyUnload(mod):
	#DO NOT USE THIS PLZ
	global loaded_modules
	if loaded_modules.has_key(mod.Module): del(loaded_modules[mod.Module])
	if sys.modules.has_key(mod.ModuleLogicalPath): del(sys.modules[mod.ModuleLogicalPath])

def unload(modname):
	global loaded_modules
	if not loaded_modules.has_key(modname):
		raise ModuleError("Module %s is not loaded"%modname)
	
	error=None
	try:
		loaded_modules[modname].ModuleObject.cleanup()
	except Exception as e:
		error=e
	
	forciblyUnload(loaded_modules[modname])
	if error is not None:
		raise ModuleError("Module %s did not clean up properly!  This could lead to instability. Because: %s"%(modname, str(error)))

def refreshList():
	global loaded_modules, available_modules
	available_modules={}
	for f in glob.glob('modules/*'):
		if not f.endswith(('.py', '.pyc')) or f.find('__init__')>=0: continue
		try:
			mod_data=parseHeader(f)
		except ModuleError as e:
			log.debug(str(e))
			continue
		available_modules[mod_data.Module]=mod_data

def listNew():
	global loaded_modules, available_modules
	new_modules=[]
	for avail in available_modules.values():
		if avail.Module not in loaded_modules.keys(): new_modules.append(avail)
	return new_modules

def listMissing():
	global loaded_modules, available_modules
	missing_modules=[]
	for loaded in loaded_modules.values():
		if loaded.Module not in available_modules.keys(): missing_modules.append(loaded)
	return missing_modules

def listUpgraded():
	global loaded_modules, available_modules
	upgraded_modules=[]
	for loaded in loaded_modules.values():
		if loaded.Module in available_modules.keys():
			avail=available_modules[loaded.Module]
			if avail.Version>loaded.Version: upgraded_modules.append(avail)
	return upgraded_modules

def parseHeader(filename):
	isdotmod=False
	if filename.endswith('.pyc'):
		#a .module file is required
		oldfilename=filename
		filename=filename.replace('.pyc', '.module')
		isdotmod=True
	
	try:
		fh=open(filename, 'r')
	except IOError:
		if isdotmod:
			raise ModuleError("No matching .module file for %s (expecting %s)"%(oldfilename, filename))
		else:
			raise ModuleError("No such module file %s"%(filename))
	
	mod_header_dict={}
	current_key=""
	current_text=[]
	while True:
		line=fh.readline()
		if not line: break
		if isdotmod:
			line=line.rstrip()
			if not current_key: line=line.lstrip()
		else:
			line=line.strip()
			if line and line[0]!='#': break #end of comments
			line=line[1:]
		
		if not line:
			if not current_key: continue
			mod_header_dict[current_key]="\n".join(current_text)
			current_key=""
			current_text=[]
			continue
		
		if not current_key:
			current_key, current_text=line.split(":", 1)
			current_key=current_key.strip()
			current_text=[current_text.strip()]
		else:
			current_text.append(line)
	
	if current_key: mod_header_dict[current_key]="\n".join(current_text)
	try:
		return LoadableModule(ModuleFilename=(oldfilename if isdotmod else filename), InfoFilename=filename, ModuleLogicalPath='modules.'+mod_header_dict['Module'], **mod_header_dict)
	except ModuleError as e:
		raise ModuleError(str(e)+(" [in %s]"%(filename)))
		
	fh.close()
