# -*- coding: utf-8 -*-
# Windows 7 Magnifier Integration Addon for NVDA
#
# This file is covered by the GNU General Public License.
# You can read the licence by clicking Help->License in the NVDA menu
# or by visiting http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
#

import appModuleHandler
import os
import config
from configobj import *

config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'windows7magnifier.ini')
config = ConfigObj()
config.filename = config_file

class AppModule(appModuleHandler.AppModule):

	def sleep(self):
		sleepMode = config.conf["magnifier"]["muteNVDA"]
