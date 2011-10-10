import sys, os, signal, time

daemonStdin			=	'/dev/null'
daemonStderr		=	'/dev/null'
daemonStdout		=	'/dev/null'
daemonPIDFile		=	'./daemon.pid'
isDaemon			=	False

class DaemonError(Exception): pass

def daemonize():
	#Borrowed from : http://www.enterpriseitplanet.com/networking/features/article.php/3786386/Creating-a-Daemon-with-Python.htm
	#the basic idea is fork once, use setsid to become session leader, fork a second time, and then redirect stdin/stdout/stderr
	global daemonStdin, daemonStderr, daemonStdout, daemonPIDFile, isDaemon
	
	#First thing to do is to try to open the files we will be redirecting std* to.
	try:
		newStdin=open(daemonStdin, 'r')
		newStdout=open(daemonStdout, 'a+')
		newStderr=open(daemonStderr, 'a+', 0)
	except Exception as e:
		raise DaemonError("Can't redirect stdin/stdout/stderr: "+str(e))
	
	#If we can open those files, then we try to fork into the background.
	try:
		pid=os.fork()
		if pid>0:
			#In the parent
			sys.exit(0)
		os.setsid() #Set the new process (child) to be the session leader
		final_pid=os.fork()
		if final_pid>0:
			#Again, in the parent - now we have to write the PIDfile and exit
			pidfile=file(daemonPIDFile, 'w')
			pidfile.write(str(final_pid))
			pidfile.close()
			sys.exit(0)
	except OSError as e:
		raise DaemonError("Can't fork: "+str(e))
	
	isDaemon=True
	
	try:
		for f in (sys.stdout, sys.stderr): f.flush()
		for fd in (sys.stdin, sys.stdout, sys.stderr):
			if fd.fileno()>0:
				fd.close()
	except OSError as e:
		pass #Do nothing, we don't care really, since we're no longer using stdin/stdout/stderr
	
	sys.stdin=newStdin
	sys.stdout=newStdout
	sys.stderr=newStderr
	#we're now a real daemon

def isRunning():
	return os.path.isfile(daemonPIDFile)

def getPID():
	if not isRunning(): return 0
	pidfile=file(daemonPIDFile, 'r')
	pid=int(pidfile.readline())
	pidfile.close()
	return pid

def start():
	#Doesn't do anything - simply checks if we're already running
	return not isRunning()

def stop():
	pid=getPID()
	if pid<1: raise DaemonError("Daemon is not running")
	try:
		os.kill(pid, signal.SIGINT)
	except OSError as e:
		raise DaemonError("Couldn't send SIGINT to PID %d: %s"%(pid, str(e)))
	os.remove(daemonPIDFile)
	return True

def restart():
	stop()
	return start()

def rehash():
	pid=getPID()
	if pid<1: raise DaemonError("Daemon is not running")
	try:
		os.kill(pid, signal.SIGHUP)
	except OSError as e:
		raise DaemonError("Couldn't send SIGHUP to PID %d: %s"%(pid, str(e)))
	return True
