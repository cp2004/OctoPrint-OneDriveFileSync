$(function () {
    function OneDriveFilesNavbarVM(parameters) {
        const self = this;

        self.settingsViewModel = parameters[0];
        self.printerStateViewModel = parameters[1];

        self.syncing = ko.observable(false);

        self.syncStatusClass = ko.pureComputed(function () {
            if (!self.settingsViewModel.settings.plugins.onedrive_files.sync.while_printing() && self.printerStateViewModel.isPrinting()) {
                return "fas fa-pause"
            } else if (self.syncing()){
                return "fas fa-sync"
            } else {
                return "fas fa-check"
            }
        })

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "onedrive_files") {
                return
            }

            if (data.type === "sync_start") {
                self.syncing(true)
            } else if (data.type === "sync_end") {
                self.syncing(false)
            }
        }
    }

    window.OCTOPRINT_VIEWMODELS.push({
        construct: OneDriveFilesNavbarVM,
        name: "OneDriveFilesNavbarViewModel",
        dependencies: ["settingsViewModel", "printerStateViewModel"],
        elements: ["#navbar_plugin_onedrive_files"]
    })
})
