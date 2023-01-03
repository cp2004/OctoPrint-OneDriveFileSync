# coding=utf-8
from __future__ import absolute_import

from pathlib import Path

import octo_onedrive.onedrive
import octoprint.plugin

from . import _version, sync, api

APPLICATION_ID = "192e2408-1e4e-49bb-96af-fef02c7c2433"  # Not a secret :)


class OneDriveFilesSyncPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
):
    sync_worker: sync.OneDriveSyncWorker
    onedrive: octo_onedrive.onedrive.OneDriveComm
    api: api.OneDriveFilesApi

    def initialize(self):



        # Create the 'OneDrive' folder if it doesn't exist
        self._file_manager.add_folder("local", "OneDrive", ignore_existing=True)

        def get_config():
            return {
                "mode": self._settings.get(["sync", "mode"]),
                "interval": self._settings.get(["sync", "interval"]),
                "onedrive_folder": self._settings.get(["folder", "id"]),
                "octoprint_folder": "OneDrive",
                "max_depth": self._settings.get(["sync", "max_depth"]),
            }

        def sync_condition():
            # TODO configurable
            return not self._printer.is_printing()

        self.onedrive = octo_onedrive.onedrive.OneDriveComm(
            APPLICATION_ID,
            ["Files.ReadWrite"],
            str(Path(self._settings.get_plugin_data_folder()) / "token_cache.bin"),
            "https://login.microsoftonline.com/consumers",
            # encryption_key=self._settings.global_get(["server", "secretKey"]),
        )

        # Test starting the sync worker
        self.sync_worker = sync.OneDriveSyncWorker(
            config=get_config,
            onedrive=self.onedrive,
            octoprint_filemanager=self._file_manager,
            sync_condition=sync_condition,
            on_log=lambda log, msg: None,
        )
        self.sync_worker.start()

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

    def get_api_commands(self):
        return api.Commands.list_commands()

    def on_api_command(self, command, data):
        return self.api.on_api_command(command, data)

    def on_api_get(self, request):
        return self.api.on_api_get(request)

    def sync_now(self):
        self.sync_worker.sync_now()

    def on_shutdown(self):
        self.sync_worker.stop()

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
