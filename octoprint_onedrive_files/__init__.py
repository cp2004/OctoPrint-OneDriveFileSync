# coding=utf-8
from __future__ import absolute_import

from pathlib import Path

import octo_onedrive.onedrive
import octoprint.plugin
from octoprint.util.version import is_octoprint_compatible

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
        self.api = api.OneDriveFilesApi(self)

        # Create the 'OneDrive' folder if it doesn't exist
        self._file_manager.add_folder("local", "OneDrive", ignore_existing=True)

        def get_config():
            return {
                "mode": self._settings.get(["sync", "mode"]),
                "interval": self._settings.get_int(["sync", "interval"]),
                "onedrive_folder": self._settings.get(["folder", "id"]),
                "octoprint_folder": "OneDrive",
                "max_depth": self._settings.get_int(["sync", "max_depth"]),
            }

        def sync_condition():
            if self._settings.get(["sync", "automatic"]):
                if self._settings.get(["sync", "while_printing"]):
                    return True
                else:
                    return not self._printer.is_printing()
            else:
                return False

        def on_sync_start():
            self.send_message("sync_start", {})

        def on_sync_end():
            self.send_message("sync_end", {})

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
            on_sync_start=on_sync_start,
            on_sync_end=on_sync_end,
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
                "max_depth": 6,
                "automatic": True,
                "while_printing": False,
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

    def send_message(self, msg_type: str, msg_content: dict):
        self._plugin_manager.send_plugin_message(
            "onedrive_files", {"type": msg_type, "content": msg_content}
        )

    # AssetPlugin mixin
    def get_assets(self):
        assets = {"js": ["dist/onedrive_backup.js", "viewmodels/settings.js", "viewmodels/navbar.js"]}

        if is_octoprint_compatible("<=1.9.0"):
            # Add icon transform CSS
            assets["css"] = ["css/fa5-power-transform.min.css"]

        return assets

    # Softwareupdate hook
    def get_update_information(self):
        return {
            "onedrive_files": {
                "displayName": "OneDrive File Sync",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "cp2004",
                "repo": "OctoPrint-OneDriveFileSync",
                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "comittish": ["main"],
                },
                "prerelease_branches": [
                    {
                        "name": "Release Candidate",
                        "branch": "pre-release",
                        "comittish": ["pre-release", "main"],
                    }
                ],
                "current": self._plugin_version,
                "pip": "https://github.com/cp2004/OctoPrint-OneDriveFileSync/releases/download/{target_version}/release.zip",
            }
        }


__plugin_name__ = "OneDrive File Sync"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_version__ = _version.get_versions()["version"]


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OneDriveFilesSyncPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
