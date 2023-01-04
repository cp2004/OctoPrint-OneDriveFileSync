$(function () {
    function OneDriveFilesSettingsVM(parameters) {
        const self = this;

        self.settingsViewModel = parameters[0];

        self.syncModeHelp = ko.pureComputed(function () {
            const syncMode = self.settingsViewModel.settings.plugins.onedrive_files.sync.mode();
            if (syncMode === "onedrive") {
                return gettext("OneDrive → OctoPrint sync. The OctoPrint folder will be synced to always be the same as the OneDrive folder")
            } else if (syncMode === "octoprint") {
                return gettext("OctoPrint → OneDrive sync. The OneDrive folder will be synced to always be the same as the OctoPrint folder")
            } else if (syncMode === "two") {
                return gettext("(Experimental) OneDrive ↔ OctoPrint sync.")
            }
        })
    }

    window.OCTOPRINT_VIEWMODELS.push({
        construct: OneDriveFilesSettingsVM,
        name: "OneDriveFilesSettingsViewModel",
        dependencies: ["settingsViewModel"],
        elements: ["#onedrive_files_viewmodel"]
    })
})
