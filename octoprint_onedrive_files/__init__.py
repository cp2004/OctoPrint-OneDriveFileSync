# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

class OneDriveFilesSyncPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin
):

    # SettingsPlugin mixin
    def get_settings_defaults(self):
        return {
            "onedrive_folder": {
                "id": "",
                "name": "",
            },
            # Sync modes: 
            # OctoPrint => OneDrive
            # OneDrive => OctoPrint
            # Both ways
            "sync_mode": "all"
        }

    # AssetPlugin mixin
    def get_assets(self):
        return {
            "js": ["js/onedrive_files.js"],
            "css": ["css/onedrive_files.css"],
            "less": ["less/onedrive_files.less"]
        }

    # Softwareupdate hook
    def get_update_information(self):
        return {
            "onedrive_files": {
                "displayName": "OneDrive Files",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "cp2004",
                "repo": "OctoPrint-OneDriveFiles",
                "current": self._plugin_version,
                "pip": "https://github.com/cp2004/OctoPrint-OneDriveFiles/archive/{target_version}.zip",
            }
        }

__plugin_name__ = "Onedrive Files Sync"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OneDriveFilesSyncPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
