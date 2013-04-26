# -*- coding: utf-8 -*-
# Windows 7 Magnifier Integration Addon for NVDA
#
# This file is covered by the GNU General Public License.
# You can read the licence by clicking Help->License in the NVDA menu
# or by visiting http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
#

import appModuleHandler
import config

class AppModule(appModuleHandler.AppModule):
	sleepMode = config.conf["magnifier"]["muteNVDA"]
