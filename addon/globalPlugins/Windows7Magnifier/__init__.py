# -*- coding: utf-8 -*-
# Windows 7 Magnifier Integration Addon for NVDA
#
# This file is covered by the GNU General Public License.
# You can read the licence by clicking Help->License in the NVDA menu
# or by visiting http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
#
# This addon integrates configuration options into the standard NVDA GUI
# To access, select "Preferences", "Magnifier Options" from the NVDA GUI
#
# Shortcuts:
# 	NVDA+SHIFT+m:	Toggle the screen magnifier
# 	NVDA+i:			Toggle color inversion
# 	NVDA+plus:		Zoom in
# 	NVDA+minus:		Zoom out
#
########################################################################

# Standard Python Imports
import os
import sys
import subprocess
import time
import threading

# NVDA imports
import ui
import globalPluginHandler
import winUser
import win32api
import ctypes
import win32con
import api
import gui
import wx
import tones
import speech
import keyboardHandler
import addonHandler
addonHandler.initTranslation()
from logHandler import log 

import Windows7MagnifierConfig

# Win32 Constants - Controlling windows
#WS_EX_NOACTIVATE = 0x8000000L
#WS_EX_TOPMOST = 0x00000008L
#WS_EX_WINDOWEDGE = 0x00000100L 
#WS_EX_APPWINDOW = 0x00040000L
#WS_EX_LAYERED = 0x00080000
#WS_EX_TOOLWINDOW = 0x00000080L

GWL_EXSTYLE = -20
WM_CLOSE = 0x10
WM_MOVE = 0x0003
SWP_NOACTIVATE = 0x10
SWP_NOSIZE = 0x01
SWP_NOMOVE = 0x02
SWP_NOZORDER = 0x04
SWP_SHOWWINDOW = 0x40
SW_FORCEMINIMIZE = 11
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7

GW_CHILD = 5

# Win32 Constants - Keyboard
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
KEYEVENTF_KEYUP = 0x02

# Win32 Constants - Controls
BM_CLICK = 0xF5
BM_GETCHECK = 0xF0
BM_SETCHECK = 0xF1
BST_UNCHECKED = 0x00
BST_CHECKED = 0x01
TBM_GETPOS = 0x400
TBM_SETPOSNOTIFY = 0x422

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	""" Please see description at the top of this file.
	"""
	_instance = None
	
	def __init__(self):
		""" Class is instantiated during NVDA startup
		"""
		# Allow parent class to process
		super(GlobalPlugin, self).__init__()
		
		# Singleton - so other classes can easily access w/out needing a
		# reference
		GlobalPlugin._instance = self
		
		# Keep track of primary thread, so long-running functions can
		# detect it and be pushed to background threads
		self.mainThread = threading.currentThread()
		
		# Add magnifier options to the NVDA preferences menu
		prefsMenu = gui.mainFrame.sysTrayIcon.menu.FindItemByPosition(0).SubMenu
		item = prefsMenu.FindItem(_("M&agnifier settings..."))
		if item == -1:
			item = prefsMenu.Append(wx.ID_ANY, _("M&agnifier settings..."), _("Magnifier settings"))
		else:
			item = prefsMenu.FindItemById(item)
		
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onMagnifierSettingsCommand, item) 

		# The ID's of the controls in the (real) magnifier options
		# dialog. We need to know these so we can check/uncheck them to
		# match the user's wishes
		self.controlIDs = {
			"invertColors" : 319,
			"followMouse": 315,
			"followKeyboard": 316,
			"followTextInsertion": 317,
			"magnifierSize": 309,
			"lensSizeHorizontal": 321,
			"lensSizeVertical": 323,
			"okButton": 1
		}
		
		# Launch the magnifier if it's configured to start w/ NVDA
		if Windows7MagnifierConfig.conf["magnifier"]["startWithNVDA"]:
			self.configuring = True
			self.startMagnifier()
			self.configuring = False
			ui.message(_("Magnifier launched"))
			
		self.configuring = False
		
	def terminate(self): 
		""" Called when NVDA is done with the plugin
		"""
		# Close the magnifier if it's configured to close w/ NVDA
		if Windows7MagnifierConfig.conf["magnifier"]["closeWithNVDA"]:
			self.closeMagnifier()

		super(GlobalPlugin, self).terminate()
		
	def onMagnifierSettingsCommand(self, evt):
		""" Called when the user selects Magnifier Settings from the
			NVDA menu
			@param evt: the event which caused this action
		"""
		# Launch the settings dialog just like other settings dialogs
		gui.mainFrame._popupSettingsDialog(MagnifierSettingsDialog)

	def script_toggleMagnifier(self, gesture):
		""" Kill the magnifier if it's running, start it if it's not
			@param gesture: the gesture which caused this action
		"""
		if self.isMagnifierRunning():
			ui.message("Closing magnifier")
			# Pause so the speech can complete uninterrupted
			time.sleep(1)
			self.closeMagnifier()
		else:
			self.startMagnifier()

	def script_zoomIn(self, gesture):
		""" 
			Increase the zoom level
			@param gesture: the gesture which caused this action
		""" # Simulate the Windows (built-in) hotkey for zooming in
		self._pressKey([winUser.VK_LWIN, VK_OEM_PLUS])
		try:
			tones.beep(800, 50)
		except:
			pass
		
		# Windows will automatically launch the magnifier on zoom adjust
		# If this happens, the windows need to be hidden (if configured)
		self.hideWindows()
		
	def script_zoomOut(self, gesture):
		""" Decrease the zoom level
			@param gesture: the gesture which caused this action
		"""
		# Simulate the Windows (built-in) hotkey for zooming out
		self._pressKey([winUser.VK_LWIN, VK_OEM_MINUS])
		try:
			tones.beep(400, 50)
		except:
			pass
		
		# Windows will automatically launch the magnifier on zoom adjust
		# If this happens, the windows need to be hidden (if configured)
		self.hideWindows()

	def script_invert(self, guesture):
		""" Invert the screen colors
			@param gesture: the gesture which caused this action
		"""
		# Windows does not automatically launch the magnifier for color
		# inversion, so we need to start it
		if not self.isMagnifierRunning():
			self.startMagnifier()
			
		# Simulate the Windows (built-in) hotkey for color inversion
		self._pressKey([winUser.VK_CONTROL, winUser.VK_MENU, 'i'])
		# Toggle in the config
		Windows7MagnifierConfig.conf["magnifier"]["invertColors"] = not Windows7MagnifierConfig.conf["magnifier"]["invertColors"]
		try:
			tones.beep(1000, 50)
		except:
			pass

	def isMagnifierRunning(self):
		""" Determine if the Windows magnifier is running
			@returns: True if running, False if not
			@rtype: boolean
		"""
		return None != searchProcessList("magnify.exe")

	def startMagnifier(self, block=True, applyConfig=True):
		""" Launch the Windows magnifier"
			@param block: don't return until confirmed running
			@param type: boolean
		"""
		# don't launch if already running
		if not self.isMagnifierRunning():
			ui.message(_("Launching magnifier"))
			
			# Force 64-bit version on 64-bit OS
			winDir = os.path.expandvars("%WINDIR%")
			if os.path.isfile(winDir + "\\Sysnative\\Magnify.exe"):
				process = subprocess.Popen([winDir + "\\Sysnative\\Magnify.exe"], shell=True)
			else:
				process = subprocess.Popen([winDir + "\\System32\\Magnify.exe"], shell=True)

		if block or applyConfig:
			self._waitForMagnifierWindow()
			time.sleep(1)
				
		if applyConfig:
			self.applyConfig()

	def detectCurrentMode(self):
		""" Try to determine the current executing mode. This works by 
			looking for mode-specific windows.
			@returns 'Fullscreen', 'Lens', or 'Docked'
		"""
		modes = {
			"Fullscreen": ("Screen Magnifier Fullscreen Window", None),
			"Lens": ("Screen Magnifier Lens Window", None),
			"Docked": ("Screen Magnifier Window", None)
		}
		for mode,args in modes.items():
			if winUser.user32.FindWindowA(args[0], args[1]) != 0:
				return mode
				
		return None
		
	def closeMagnifier(self):
		""" Close the magnifier
		"""
		# Find the window, send it the standard win32 message to close
		winUser.sendMessage(
			winUser.user32.FindWindowA("MagUIClass", None),
			WM_CLOSE, 0, 0
		)

	def applySettings(self, mode=None, invertColors=None, followMouse=None, followKeyboard=None, followTextInsertion=None, lensSizeHorizontal=None, lensSizeVertical=None):
		""" Apply the (supplied) options in the Windows magnifier
			settings dialog.
			@param mode: 'Fullscreen', 'Docked', or 'Lens'
			@param invertColors: Enable/disable color inversion
			@param followMouse: Enable/disable mouse cursor tracking
			@param followKeyboard: Enable/disable keyboard tracking
			@param followTextInsertion: Enable/disable text cursor
				tracking
			@param lensSizeHorizontal: The horizontal size of the lens
			@param lensSizeVertical: The vertical size of the lens
			@raise ValueError if all tracking options are supplied and 
				all are False
		"""
		self.configuring = True
		self.startMagnifier(block=True, applyConfig=False)
		
		if mode != None and self.detectCurrentMode() != mode:
			hwnd = self._waitForMagnifierWindow()
			
			if mode == "Fullscreen":
				self._pressKey([winUser.VK_CONTROL, winUser.VK_MENU, 'f'])
			if mode == "Docked":
				self._pressKey([winUser.VK_CONTROL, winUser.VK_MENU, 'd'])
			elif mode == "Lens":
				self._pressKey([winUser.VK_CONTROL, winUser.VK_MENU, 'l'])

			log.debug("Magnifier - Mode changed to %s" % mode)
			time.sleep(1)
			
			for i in range(250):
				if self.detectCurrentMode() == mode: break
				time.sleep(0.02)
			
			# When switching between modes, the window likes to be
			# shuffled. Without this, other settings do not get applied
			# properly
			mainWindow = self._waitForMagnifierWindow()
			self._hideWindow(mainWindow)
			self._showWindow(mainWindow)
			self._hideWindow(mainWindow)
		
		# If tracking options are specified, at least one must be enabled
		inputOK = False
		for trackingOption in [followMouse, followKeyboard, followTextInsertion]:
			if trackingOption == None or trackingOption == True:
				inputOK = True
				break
		if not inputOK: raise ValueError("If all tracking options are supplied, at least one must be enabled")

		checkboxes = [
			("invertColors", invertColors),
			("followMouse", followMouse),
			("followKeyboard", followKeyboard),
			("followTextInsertion", followTextInsertion)
		]
		
		# Magnifier will complain if you uncheck all tracking options.
		# So we must mark all the CHECKED boxes first
		checkboxes = sorted(checkboxes, key=lambda boxArgs: not boxArgs[1])

		# Open the settings dialog and grab controls
		[dialog, controls] = self.openSettings()
	
		# Loop through each setting
		for boxArgs in checkboxes:
			name = boxArgs[0]
			# if its value is specified in the arguments
			# AND if there's a control for it, set it appropriately
			if not name in controls:
				log.debug("Magnifier: Could not find control %s" % name)
			if boxArgs[1] != None and name in controls:
				log.debug("Magnifier: Setting %s %s" % (name, boxArgs[1]))
				controls[name].setChecked(boxArgs[1])
		
		# Set the lens size
		if lensSizeHorizontal != None: controls["lensSizeHorizontal"].setTrackbarValue(lensSizeHorizontal - 10)
		if lensSizeVertical != None: controls["lensSizeVertical"].setTrackbarValue(100 - lensSizeVertical)
		
		# Close the dialog
		time.sleep(0.25)
		keyboardHandler.KeyboardInputGesture.fromName("enter").send()
		# Pause for a moment - helps with windows behaving
		time.sleep(0.25)

		self.configuring = False
		self.hideWindows()
		
	def openSettings(self):
		""" Opens the (real) settings window
			@returns The hwnd to the settings window and a list of each 
			(relevant) control in that window
		"""
		# make sure the magnifier is running
		self.startMagnifier(block=True, applyConfig=False)

		# So... find the window
		mainWindow = self._waitForMagnifierWindow()
		self._showWindow(mainWindow, True)

		controls = winUser.getWindow(mainWindow, GW_CHILD)
		# short pause to help make sure the window has focus
		time.sleep(0.1)
		# click on the settings button
		self._click(160, 15, controls)

		# Wait for options window to be visible (but don't wait forever)
		optionsWindow = self._waitForWindow(windowName=_("Magnifier Options"))
	
		# Grab the contros so we can return them to the caller
		controls = {}
		for name,controlID in self.controlIDs.items():
			controls[name] = Win32Control(optionsWindow, controlID)
			
		return optionsWindow, controls

	def hideWindows(self, numberOfChecks=2, delayBetweenChecks=0.1, minimizeForce=False):
		""" Hide the (real) magnifier's control windows. This includes
			the standard window, the magnifier icon, and the settings
			dialog.
			
			This function will push itself to a daemon thread for 
			background processing, so it doesn't lock up NVDA. This is
			because the function may take a while to complete, as it can
			check repeatedly for windows to re-appear.
			
			@param numberOfChecks: number of times to check for each
				window
			@param delayBetweenChecks: how long to wait before checking
				for windows' appearance
		"""
		# Exit if the user has configured windows to stay open
		if self.configuring or not Windows7MagnifierConfig.conf["magnifier"]["hideMagnifierControls"]: return
		
		# Detect if the calling thread is main NVDA thread
		if threading.currentThread() == self.mainThread:
			# If it is, call this function inside a new thread and exit
			t = threading.Thread(target=self.hideWindows, args=(numberOfChecks, delayBetweenChecks))
			t.daemon = True
			t.start()
			return

		time.sleep(1)
		# Window classes and names to search for
		windowArgs = [
			("MagUIClass", None),
		]
		
		# Check for windows repeatedly, hide them if they are found
		for i in range(numberOfChecks):
			for args in windowArgs:
				hwnd = winUser.user32.FindWindowA(args[0], args[1])
				if hwnd != 0:
					self._hideWindow(hwnd)
			# don't be a resource-hog, pause a bit between checks
			time.sleep(delayBetweenChecks)
		
	def _type(self, string):
		for c in string:
			self._pressKey(self._virtualizeKeys([c]))

	def _pressKey(self, keyCodes):
		""" Internal function used to simulate a key press. This is used
			to map this addon's hotkeys to Windows 7 Magnifier hotkeys
			@param keyCodes: A list of virtual key codes. All supplied
				will be pressed simultaneously.
		"""
		keyCodes = self._virtualizeKeys(keyCodes)
		
		# Simulate each key being pressed down (in order)
		for key in keyCodes:
			winUser.user32.keybd_event(key, key, 0, 0)

		# Simulate each key being released (in reverse order)
		keyCodes.reverse()
		for key in keyCodes:
			winUser.user32.keybd_event(key, key, KEYEVENTF_KEYUP, 0)
			
	def _releaseKeys(self, keyCodes, allModifiers=False):
		""" Ensure keyboard buttons are released.
			Some actions simulate key presses, and these don't behave
			properly if the user still has keys depressed.
		"""
		keyCodes = self._virtualizeKeys(keyCodes)
		
		if allModifiers:
			keyCodes.append(winUser.VK_LWIN)
			keyCodes.append(winUser.VK_RWIN)
			keyCodes.append(winUser.VK_MENU)
			keyCodes.append(winUser.VK_CONTROL)
			keyCodes.append(winUser.VK_SHIFT)
			keyCodes.append(winUser.VK_CAPITAL)
			keyCodes.append(winUser.VK_NUMLOCK)

		for key in keyCodes:
			winUser.user32.keybd_event(key, key, KEYEVENTF_KEYUP, 0)
			
	def _hideWindow(self, hwnd):
		""" Internal convenience function to hide a window
			@param hwnd: A handle to the window to be hidden
		"""
		if self.configuring == True: return
		winUser.user32.ShowWindow(hwnd, SW_SHOWMINNOACTIVE)
		
	def _showWindow(self, hwnd, makeForeground=True):
		""" Internal convenience function to make a window visible
			@param hwnd: A handle to the window to be shown
			@param makeForeground: if True bring the window to the front
			@param waitForVisible: if True block until window is visible
		"""
		winUser.user32.ShowWindow(hwnd, win32con.SW_RESTORE)
		if makeForeground:
			winUser.setForegroundWindow(hwnd)
				
	def _waitForMagnifierWindow(self, maxChecks=100, delayBetweenChecks=0.1):
		""" Block until the main magnifier window is available
			@param maxChecks: the maximum number of times to check for a
				window
			@param delayBetweenChecks: how long to pause between checks
		"""
		mainWindow = self._waitForWindow(windowClass="MagUIClass", windowName=None, maxChecks=maxChecks, delayBetweenChecks=delayBetweenChecks)
		return mainWindow
		
	def _waitForWindow(self, windowClass=None, windowName=None, maxChecks=100, delayBetweenChecks=0.1):
		""" Block until a given window is available
			@param windowClass: the class to search for
			@param windowName: the name to search for
			@param maxChecks: the maximum number of times to check for a
				window
			@param delayBetweenChecks: how long to pause between checks
		"""
		if windowClass != None:
			windowClass = windowClass.encode("ascii", "ignore")
		if windowName != None:
			windowName = windowName.encode("ascii", "ignore")
		log.debug("Waiting for window '%s', '%s'" % (windowClass, windowName))
		hwnd = 0
		for i in range(maxChecks):
			if hwnd == 0:
				hwnd = winUser.user32.FindWindowA(windowClass, windowName)
				
			if hwnd != 0:
				break
			else:
				time.sleep(delayBetweenChecks)
			
		return hwnd

	def _virtualizeKeys(self, keyCodes):
		""" Convert chars to their Virtual Key equivalents
			@param keyCodes: A list of chars to convert
		"""
		for i in range(len(keyCodes)):
			# If it's not a string, assume it's already a VK
			if isinstance(keyCodes[i], basestring):
				keyCodes[i] = winUser.VkKeyScanEx(keyCodes[i], winUser.user32.GetKeyboardLayout(0))[1]
				
		return keyCodes
			
	@staticmethod
	def applyConfig():
		""" Apply the configured magnifier options set from the NVDA
			preferences to the (real) magnifier
		"""
		if Windows7MagnifierConfig.conf["magnifier"]["mode"] == "Lens":
			gui.ExecAndPump(
				GlobalPlugin._instance.applySettings,
				mode = Windows7MagnifierConfig.conf["magnifier"]["mode"],
				invertColors = Windows7MagnifierConfig.conf["magnifier"]["invertColors"],
				lensSizeHorizontal = Windows7MagnifierConfig.conf["magnifier"]["lensSizeHorizontal"],
				lensSizeVertical = Windows7MagnifierConfig.conf["magnifier"]["lensSizeVertical"]
			)
		else:
			# Fullscreen and docked have identical settings
			gui.ExecAndPump(
				GlobalPlugin._instance.applySettings,
				mode = Windows7MagnifierConfig.conf["magnifier"]["mode"],
				invertColors = Windows7MagnifierConfig.conf["magnifier"]["invertColors"],
				followMouse = Windows7MagnifierConfig.conf["magnifier"]["followMouse"],
				followKeyboard = Windows7MagnifierConfig.conf["magnifier"]["followKeyboard"],
				followTextInsertion = Windows7MagnifierConfig.conf["magnifier"]["followTextInsertion"]
			)

		ui.message("Settings applied")
			
		# beep to indicate readiness
		for i in range(3):
			try:
				time.sleep(.1)
				tones.beep(550 + i*50, 50)
			except Exception, e:
				pass

	def _click(self, x, y, hwnd=0):
		""" Simulate a mouse click
			@param x: the X coordinate to click
			@param y: the Y coordinate to click
			@param hwnd: The window to click. If specified, the coords
				are relative to the window
		"""
		# Grab the current position so we can move the mouse back when
		lastPos = win32api.GetCursorPos()
		
		if hwnd != 0:
			# make the coordinates relative to the specified window
			offset = winUser.ScreenToClient(hwnd, 0, 0)
			x -= offset[0]
			y -= offset[1]
			winUser.setForegroundWindow(hwnd)
		
		# move the mouse and click
		win32api.SetCursorPos((x,y))
		win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
		win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)
		
		# restore the previous mouse position
		win32api.SetCursorPos(lastPos)
		
	__gestures={
		"kb:NVDA+shift+m": "toggleMagnifier",
		"kb:NVDA+plus": "zoomIn",
		"kb:NVDA+=": "zoomIn",
		"kb:NVDA+-": "zoomOut",
		"kb:NVDA+i": "invert",
	}

class Win32Control:
	""" The controls in the Window 7 Magnifier options dialog only bind
		to the generic NVDAObject class... more likely: I don't really
		know what I'm doing. To work around either case, a wrapper class
	"""
	
	def __init__(self, parentHWND, controlID):
		""" @param parentHWND: A handle to the parent window
			@param controlID: The ID of the control. These (apparently)
				are pretty reliably static, even between executions
		"""
		self.parentHWND = parentHWND
		self.controlID = controlID
		
		# use a Win32 function to convert the controlID to a handle
		self.hwnd = winUser.user32.GetDlgItem(self.parentHWND, self.controlID)

	def setTrackbarValue(self, value):
		""" Set the value of a trackbar control
			@param value: The new value to assign
		"""
		# TBM_SETPOSNOTIFY is used, or the value doesn't actually take
		winUser.sendMessage(self.hwnd, TBM_SETPOSNOTIFY, True, value)

	def setChecked(self, checked):
		""" Sets a checkbox's state
			@param checked: True for a check, False for unchecked
		"""
		# if desired state doesn't match current state, simulate a click
		if checked != self.isChecked():
			self.click()
		 
	def isChecked(self):
		""" Determine the state of a checkbox
			@returns True if checked, False if not
		"""
		# The win32 function for checking returns a 1 if checked
		return 1 == winUser.sendMessage(self.hwnd, BM_GETCHECK, 0, 0)
		
	def toggleCheck(self):
		""" Toggle the state of a checkbox
		"""
		self.click()
		
	def click(self):
		""" Simulate a mouse click on the control
		"""
		winUser.sendMessage(self.hwnd, BM_CLICK, 0, 0)

class MagnifierSettingsDialog(gui.SettingsDialog):
	""" A custom settings dialog, designed to function like other NVDA
		settings dialogs while being a friendlier replacement for the
		Windows 7 magnifier options dialog
	"""
	title = _("NVDA Magnifier Addon Options")

	def makeSettings(self, settingsSizer):
		""" Create controls and add them to settingsSizer
			@param settingsSizer: the container to house all controls
		"""
		# keep track of the main sizer so we can re-layout later
		self.settingsSizer = settingsSizer
		
		# modes dropdown and label
		self.modes = [_("Fullscreen"), _("Docked"), _("Lens")]
		self.modeSelector = wx.Choice(self, wx.NewId(), name=_("&Mode"), choices=self.modes)
		self.modeSelector.SetSelection(self.modes.index(Windows7MagnifierConfig.conf["magnifier"]["mode"]))
		modeSizer = wx.BoxSizer(wx.HORIZONTAL)
		modeSizer.Add(wx.StaticText(self, -1, label=_("Mode") + ":"), border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)
		modeSizer.Add(self.modeSelector)
		
		settingsSizer.Add(modeSizer, border=10, flag=wx.BOTTOM)
		
		# Make a list of checkboxes for iterative creation
		boxArgs = [
			None,
			("startWithNVDA", _("&Start the magnifier when NVDA starts")),
			("closeWithNVDA", _("&Close the magnifier when NVDA starts")),
			("hideMagnifierControls", _("&Hide the magnifier control window")),
			("muteNVDA", _("Mute NVDA when the magnifier control window has focus (requires reload)")),
			None,
			("invertColors", _("&Invert colors")),
			("followMouse", _("Follow the mouse &pointer")),
			("followKeyboard", _("Follow the &keyboard focus")),
			("followTextInsertion", _("Follow the &text insertion point"))
		]
		
		# keep track of the checkboxes so they can be easily referenced
		self.checkBoxes = {}
		# tracking options grouped in a separate sizer so it can be
		# hidden during Lens mode
		self.trackingOptionsSizer = wx.BoxSizer(wx.VERTICAL)
		for boxArg in boxArgs:
			if boxArg == None:
				settingsSizer.Add(wx.StaticLine(self), 0, wx.ALL|wx.EXPAND, 5)				
				continue
			name = boxArg[0]
			box = wx.CheckBox(self, wx.NewId(), label=_(boxArg[1]))

			self.checkBoxes[name] = box
			box.SetValue(Windows7MagnifierConfig.conf["magnifier"][name])
			if name.startswith("follow"):
				# tracking options should be hidden if in Lens mode
				# Add them to an embedded sizer for easier to hiding
				self.trackingOptionsSizer.Add(box, border=10, flag=wx.BOTTOM)
			else:
				settingsSizer.Add(box, border=10, flag=wx.BOTTOM)
				
		settingsSizer.Add(self.trackingOptionsSizer)

		# lens size (horizontal/vertical) grouped in a separate sizer
		# so it can be hidden during fullscreen/docked mode
		self.lensSizeSizer = wx.GridSizer(rows=2, cols=2)
		self.lensControls = []
		for dimension in [_("Lens &width"), _("Lens h&eight")]:
			control = wx.SpinCtrl(self, wx.NewId(), min=10, max=100, name=dimension)
			self.lensSizeSizer.Add(wx.StaticText(self, -1, label=dimension))
			self.lensSizeSizer.Add(control)
			self.lensControls.append(control)
			
		self.lensControls[0].SetValue(Windows7MagnifierConfig.conf["magnifier"]["lensSizeHorizontal"])
		self.lensControls[1].SetValue(Windows7MagnifierConfig.conf["magnifier"]["lensSizeVertical"])
		settingsSizer.Add(self.lensSizeSizer, border=27, flag=wx.BOTTOM)		
			
	def postInit(self):
		""" Called after dialog is created. Sets the focus to the top control
		"""
		self.modeSelector.Bind(wx.EVT_CHOICE, self.modeChanged)
		self.modeChanged(None)
		self.modeSelector.SetFocus()
		
	def onOk(self, evt):
		""" Event handler for OK button being pressed
			@param evt: the event which caused this action
		"""
		# make sure user has selected at least one tracking option
		trackingSelected = False
		for trackingOption in ["followMouse", "followKeyboard", "followTextInsertion"]:
			if self.checkBoxes[trackingOption].IsChecked():
				trackingSelected = True
				break
		if self.getMode() != "Lens" and not trackingSelected:
			ui.message("You must select at least one 'Follow' option")
		else:
			for name,box in self.checkBoxes.items():
				Windows7MagnifierConfig.conf["magnifier"][name] = box.IsChecked()
			
			# The mode saved in the config file should not be translated
			# It should be consistent across languages
			for mode in ["Fullscreen", "Docked", "Lens"]:
				if self.getMode() == _(mode):
					Windows7MagnifierConfig.conf["magnifier"]["mode"] = mode

			Windows7MagnifierConfig.conf["magnifier"]["lensSizeHorizontal"] = self.lensControls[0].GetValue()
			Windows7MagnifierConfig.conf["magnifier"]["lensSizeVertical"] = self.lensControls[1].GetValue()

			# save the configuration file
			Windows7MagnifierConfig.save()
			
			# apply the settings
			GlobalPlugin.applyConfig()

			super(MagnifierSettingsDialog, self).onOk(evt)
			
	def getMode(self):
		""" Convenience method to obtain currently selected mode
		"""
		return self.modes[self.modeSelector.GetCurrentSelection()]
			
	def modeChanged(self, evt):
		""" When the mode is changed, show appropriate controls, hide
				inappropriate controls
			@param evt: the event which caused this action
		"""
		if self.getMode() == "Lens":
			self.trackingOptionsSizer.ShowItems(False)
			self.lensSizeSizer.ShowItems(True)
		else:
			self.trackingOptionsSizer.ShowItems(True)
			self.lensSizeSizer.ShowItems(False)
			
		self.Layout()
		self.GetSizer().Fit(self)

def MAKELPARAM(low, high):
	""" Make an LPARAM for Win32 function calls
	"""
	shift = 32 if sys.maxsize > 2**32 else 16
	return (high << shift) | low


TH32CS_SNAPPROCESS = 0x00000002
class PROCESSENTRY32(ctypes.Structure):
	_fields_ = [
		("dwSize", ctypes.c_ulong),
		("cntUsage", ctypes.c_ulong),
		("th32ProcessID", ctypes.c_ulong),
		("th32DefaultHeapID", ctypes.c_ulong),
		("th32ModuleID", ctypes.c_ulong),
		("cntThreads", ctypes.c_ulong),
		("th32ParentProcessID", ctypes.c_ulong),
		("pcPriClassBase", ctypes.c_ulong),
		("dwFlags", ctypes.c_ulong),
		("szExeFile", ctypes.c_char * 260)
	]

def searchProcessList(imageName):
	# See http://msdn2.microsoft.com/en-us/library/ms686701.aspx
	CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
	Process32First = ctypes.windll.kernel32.Process32First
	Process32Next = ctypes.windll.kernel32.Process32Next
	CloseHandle = ctypes.windll.kernel32.CloseHandle
	hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
	pe32 = PROCESSENTRY32()
	pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
	gotProcess = Process32First(hProcessSnap, ctypes.byref(pe32))
	while gotProcess != win32con.FALSE:
		if pe32.szExeFile.lower() == imageName.lower(): return pe32
		gotProcess = Process32Next(hProcessSnap, ctypes.byref(pe32))
		
	CloseHandle(hProcessSnap)
	return None
