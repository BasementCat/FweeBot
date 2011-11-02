#Module: nickserv

# Note: You'll have to add the following entries to any networks that you plan on identifying with
#  nickserv:
#
# "NickServ": "command"
# Example: "Nickserv": "identify password"

sendPass = {}

from fwee import event, config, log, core, common

def init(): event.listen("Network/Incoming/Message/*", sendNickServ)

def cleanup(): event.unlisten(sendNickServ)

def sendNickServ(evname, net, message):
	global sendPass
	
	if not net.name in sendPass: sendPass[net.name] = 0
	
	#log.edebug("sendPass="+str(sendPass[net.name]))		#Displays sendPass for debugging purposes.
	if sendPass[net.name] == 2: return
	
	#log.edebug("NICKSERV:"+str(config.get("Networks/"+net.name+"/NickServ")))		#Displays nickserv config entry for debugging purposes.
	
	if config.get("Networks/"+net.name+"/NickServ") is None:
		consoleMessage(net.name, "No NickServ entry found in config for "+net.name+" - Bypassing NickServ module.")
		event.trigger("Network/Event/AutoJoin", net)
		sendPass[net.name] = 2
		return
	
	if config.get("Networks/"+net.name+"/NickServ") == "":
		console.Message(net.name, "NickServ entry for "+net.name+" is blank. - Bypassing NickServ module.")
		event.trigger("Network/Event/AutoJoin", net)
		sendPass[net.name] = 2
		return
	
	chkMessage = str(message).split(":",1)
	if len(chkMessage) < 2: return
	chkMessage = str(chkMessage[1]).split("!",1)
	#log.edebug("chkMessage="+str(chkMessage[0]))		#Displays chkMessage for debugging purposes.
	
	if str(chkMessage[0]) == "NickServ":
		if sendPass[net.name] == 1:
			event.trigger("Network/Event/AutoJoin", net)
			return
		
		consoleMessage(net.name, "NickServ entry found in fwee.conf for "+net.name)
		consoleMessage(net.name, "Sending NickServ password...")
		net.send("PRIVMSG NickServ :"+config.get("Networks/"+net.name+"/NickServ")+"\r\n")
		sendPass[net.name] = 1
	
	if str(chkMessage[0]) == "AuthServ":
		if sendPass[net.name] == 1:
			event.trigger("Network/Event/AutoJoin", net)
			return
		
		consoleMessage(net.name, "NickServ entry found in fwee.conf for "+net.name)
		consoleMessage(net.name, "Sending AuthServ password...")
		net.send("PRIVMSG AuthServ :"+config.get("Networks/"+net.name+"/NickServ")+"\r\n")
		sendPass[net.name] = 1

def consoleMessage(server, message):
	if message is None: return
	if message == "": return
	
	log.edebug("[%s][%s] %s", server, "nickserv", message)
