import config
import os, sys

import globalVars
import addonHandler
addonHandler.initTranslation()
from cStringIO import StringIO 
from configobj import ConfigObj, ConfigObjError 
from logHandler import log 

confspec = ConfigObj(StringIO(
"""
[magnifier]
	startWithNVDA = boolean(default=True),
	closeWithNVDA = boolean(default=True),
	hideMagnifierControls = boolean(default=True),
	muteNVDA = boolean(default=True),
	mode = string(default=Fullscreen), 
	invertColors = boolean(default=False), 
	followMouse = boolean(default=True), 
	followKeyboard = boolean(default=True), 
	followTextInsertion = boolean(default=True),
	lensSizeHorizontal = integer(default=20,min=10,max=100),
	lensSizeVertical = integer(default=25,min=10,max=100)pa,
""" 
), list_values=False, encoding="UTF-8") 
confspec.newlines = "\r\n" 

conf = None

def load(factoryDefaults=False): 
	"""Loads the configuration from the configFile. 
	It also takes note of the file's modification time so that L{save} won't lose any changes made to the file while NVDA is running. 
	""" 
	global conf, confspec
	
	configFileName = os.path.join(globalVars.appArgs.configPath, "windows7magnifier.ini") 
	if factoryDefaults: 
		conf = ConfigObj(None, configspec=confspec, indent_type="\t", encoding="UTF-8") 
		conf.filename=configFileName 
	else: 
		try: 
			conf = ConfigObj(configFileName, configspec = confspec, indent_type = "\t", encoding="UTF-8") 
		except ConfigObjError as e: 
			conf = ConfigObj(None, configspec = confspec, indent_type = "\t", encoding="UTF-8") 
			conf.filename = configFileName 
			log.warn("Error parsing configuration file: %s" % e) 
			
	# Python converts \r\n to \n when reading files in Windows, so ConfigObj can't determine the true line ending. 
	conf.newlines = "\r\n" 
	errorList = config.validateConfig(conf, config.val)
	if errorList:
		log.warn("Errors in configuration file '%s':\n%s" % (conf.filename, "\n".join(errorList)))

def save(): 
	"""Saves the configuration to the config file. 
	""" 
	#We never want to save config if runing securely 
	if globalVars.appArgs.secure: return 
	global conf 

	if not os.path.isdir(globalVars.appArgs.configPath): 
		try: 
			os.makedirs(globalVars.appArgs.configPath) 
		except OSError, e: 
			log.warning("Could not create configuration directory") 
			log.debugWarning("", exc_info=True) 
			raise e 
	try: 
		# Copy default settings and formatting. 
		conf.validate(config.val, copy=True) 
		conf.write() 
		log.info("Configuration saved") 
	except Exception, e: 
		log.warning("Could not save configuration - probably read only file system") 
		log.debugWarning("", exc_info=True) 
		raise e
