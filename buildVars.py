# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

# Full getext (please don't change)
_ = lambda x : x

# Add-on information variables
addon_info = {
	# add-on Name
	"addon-name" : "windows7magnifier",
	# Add-on description
	# TRANSLATORS: Summary for this add-on to be shown on installation and add-on information.
	"addon-summary" : _("Windows 7 Magnifier integration for the NVDA GUI"),
	# Add-on description
	# Translators: Long description to be shown for this add-on on installation and add-on information
	"addon-description" : _("""This addon integrates configuration options into the standard NVDA GUI. To access, select "Preferences", "Magnifier Options" from the NVDA GUI"""),
	# version
	"addon-version" : "1.1.1",
	# Author(s)
	"addon-author" : "Dominic Canare <mail@greenlightgo.org>",
	# URL for the add-on documentation support
	"addon-url" : "http://www.greenlightgo.org/projects/nvda/"
}

import os.path

# Define the python files that are the sources of your add-on.
# You can use glob expressions here, they will be expanded.
pythonSources = [
	os.path.join("addon", "appModules", "*.py"),
	os.path.join("addon", "globalPlugins", "Windows7Magnifier", "*.py")
]

# Files that contain strings for translation. Usually your python sources
i18nSources = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
excludedFiles = []
