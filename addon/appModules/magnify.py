# -*- coding: utf-8 -*-
# Windows 7 Magnifier Integration Addon for NVDA
#
# This file is covered by the GNU General Public License.
# You can read the licence by clicking Help->License in the NVDA menu
# or by visiting http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
#

import appModuleHandler
import os, sys

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(parentdir, "globalPlugins", "Windows7Magnifier"))
import Windows7MagnifierConfig

class AppModule(appModuleHandler.AppModule):
	sleepMode = Windows7MagnifierConfig.conf["magnifier"]["muteNVDA"]
