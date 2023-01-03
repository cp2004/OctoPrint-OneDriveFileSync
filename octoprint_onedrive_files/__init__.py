# coding=utf-8
from __future__ import absolute_import

from pathlib import Path

import octo_onedrive.onedrive
import octoprint.plugin

from . import _version, sync

APPLICATION_ID = "192e2408-1e4e-49bb-96af-fef02c7c2433"  # Not a secret :)


class OneDriveFilesSyncPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
):
    worker = None

    # SettingsPlugin mixin
    def get_settings_defaults(self):
        return {
            "folder": {
                "id": "",
                "name": "",
            },
            # Sync modes:
            # OctoPrint => OneDrive (octoprint)
            # OneDrive => OctoPrint (onedrive)
            # Two-way               (two)
            "sync": {
                "mode": "onedrive",
                "interval": 60 * 60,
                "max_depth": 4,
            },
        }

    def on_after_startup(self):
        # Create the 'OneDrive' folder if it doesn't exist
        self._file_manager.add_folder("local", "OneDrive", ignore_existing=True)

        onedrive = octo_onedrive.onedrive.OneDriveComm(
            APPLICATION_ID,
            ["Files.ReadWrite"],
            str(Path(self._settings.get_plugin_data_folder()) / "token_cache.bin"),
            "https://login.microsoftonline.com/consumers",
            # encryption_key=self._settings.global_get(["server", "secretKey"]),
        )

        def get_config():
            return {
                "mode": self._settings.get(["sync", "mode"]),
                "interval": self._settings.get(["sync", "interval"]),
                "onedrive_folder": self._settings.get(["folder", "id"]),
                "octoprint_folder": "OneDrive",
                "max_depth": self._settings.get(["sync", "max_depth"]),
            }

        # Test starting the sync worker
        self.worker = sync.OneDriveSyncWorker(
            config=get_config,
            onedrive=onedrive,
            octoprint_filemanager=self._file_manager,
            sync_condition=lambda: True,
            on_log=lambda log, msg: None,
        )
        self.worker.start()

    def on_shutdown(self):
        self.worker.stop()

    # AssetPlugin mixin
    def get_assets(self):
        return {
            "js": ["js/onedrive_files.js"],
            "css": ["css/onedrive_files.css"],
            "less": ["less/onedrive_files.less"],
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
__plugin_version__ = _version.get_versions()["version"]


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OneDriveFilesSyncPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
