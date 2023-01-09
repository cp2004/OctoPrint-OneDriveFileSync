$(function () {
    function OneDriveFilesNavbarVM(parameters) {
        const self = this

        self.settingsViewModel = parameters[0]
        self.printerStateViewModel = parameters[1]

        self.syncing = ko.observable(false)

        self.account_configured_override = ko.observable(false)
        self.folder_configured_override = ko.observable(false)

        self.configured = ko.pureComputed(function () {
            return (
                (self.account_configured_override() ||
                    self.settingsViewModel.settings.plugins.onedrive_files.accounts()
                        .length > 0) &&
                (self.folder_configured_override() ||
                    self.settingsViewModel.settings.plugins.onedrive_files.folder.id() !==
                        "")
            )
        })

        self.paused = ko.pureComputed(function () {
            return (
                !self.settingsViewModel.settings.plugins.onedrive_files.sync.while_printing() &&
                self.printerStateViewModel.isPrinting()
            )
        })

        self.syncStatusClass = ko.pureComputed(function () {
            if (self.paused()) {
                return "fas fa-pause"
            } else if (!self.configured()) {
                return "fas fa-question"
            } else if (self.syncing()) {
                return "fas fa-sync"
            } else {
                return "fas fa-check"
            }
        })

        self.syncPopoverContent = ko.pureComputed(function () {
            let msg = "Sync status: "

            if (self.paused()) {
                msg += "Paused"
            } else if (!self.configured()) {
                msg += "Not configured"
            } else if (self.syncing()) {
                msg += "Syncing..."
            } else {
                msg += "Synced"
            }

            msg = "<p>" + msg + "</p>"

            const lastSyncText = self.lastSyncText()
            if (lastSyncText && self.configured()) {
                msg += "<p>" + lastSyncText + "</p>"
            }

            if (!self.paused() && self.configured()) {
                msg += "<p><strong>Click to sync now!</strong></p>"
            }
            return msg
        })

        self.sync = function () {
            OctoPrint.simpleApiCommand("onedrive_files", "sync")
        }

        self.lastSync = ko.observable("")
        self.lastSyncText = ko.pureComputed(function () {
            if (self.lastSync() !== "") {
                return "Last sync: " + self.lastSync()
            } else {
                // Fall back to sync time given on settings load
                const last_sync =
                    self.settingsViewModel.settings.plugins.onedrive_files.last_sync()
                if (last_sync > 0) {
                    // We have synced since OctoPrint started up
                    return (
                        "Last sync: " +
                        new Date(last_sync * 1000).toLocaleTimeString()
                    )
                } else {
                    return ""
                }
            }
        })

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "onedrive_files") {
                return
            }

            if (data.type === "sync_start") {
                self.syncing(true)
            } else if (data.type === "sync_end") {
                self.lastSync(new Date().toLocaleTimeString())
                self.syncing(false)
            } else if (data.type === "auth_done") {
                // slight hack to avoid triggering yet another settings refresh
                self.account_configured_override(true)
            } else if (data.type === "folder_changed") {
                self.folder_configured_override(true)
            }
        }
    }

    window.OCTOPRINT_VIEWMODELS.push({
        construct: OneDriveFilesNavbarVM,
        name: "OneDriveFilesNavbarViewModel",
        dependencies: ["settingsViewModel", "printerStateViewModel"],
        elements: ["#navbar_plugin_onedrive_files"],
    })
})
