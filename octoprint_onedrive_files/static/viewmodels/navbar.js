$(function () {
    function OneDriveFilesNavbarVM(parameters) {
        const self = this

        self.settingsViewModel = parameters[0]
        self.printerStateViewModel = parameters[1]

        self.syncing = ko.observable(false)

        self.syncStatusClass = ko.pureComputed(function () {
            if (
                !self.settingsViewModel.settings.plugins.onedrive_files.sync.while_printing() &&
                self.printerStateViewModel.isPrinting()
            ) {
                return "fas fa-pause"
            } else if (self.syncing()) {
                return "fas fa-sync"
            } else {
                return "fas fa-check"
            }
        })

        self.syncPopoverContent = ko.pureComputed(function () {
            let msg = "Sync status: "
            const paused =
                !self.settingsViewModel.settings.plugins.onedrive_files.sync.while_printing() &&
                self.printerStateViewModel.isPrinting()

            if (paused) {
                msg += "Paused"
            } else if (self.syncing()) {
                msg += "Syncing..."
            } else {
                msg += "Synced"
            }

            msg = "<p>" + msg + "</p><p>Last Sync: " + self.lastSync() + "</p>"
            if (!paused) {
                msg += "<p><strong>Click to sync now!</strong></p>"
            }
            return msg
        })

        self.sync = function () {
            OctoPrint.simpleApiCommand("onedrive_files", "sync")
        }

        self.lastSync = ko.observable("Never")

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "onedrive_files") {
                return
            }

            if (data.type === "sync_start") {
                self.syncing(true)
            } else if (data.type === "sync_end") {
                self.lastSync(new Date().toLocaleTimeString())
                self.syncing(false)
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
