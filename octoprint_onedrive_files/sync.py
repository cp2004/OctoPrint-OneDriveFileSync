"""
Module to sync files to OneDrive


"""
import logging
import os
import threading
import copy
import pathlib
import time

import octoprint.filemanager.storage
from octoprint.filemanager import valid_file_type, DiskFileWrapper, FileDestinations
import octo_onedrive.onedrive

logger = logging.getLogger("octoprint.plugins.onedrive_files.sync")


class OneDriveSyncWorker(threading.Thread):
    def __init__(
        self,
        config: callable,
        onedrive: octo_onedrive.onedrive.OneDriveComm,
        octoprint_filemanager: octoprint.filemanager.FileManager,
        sync_condition: callable,
        on_sync_start: callable = lambda: None,
        on_sync_end: callable = lambda: None,
    ):
        super().__init__()

        self._logger = logging.getLogger("octoprint.plugins.onedrive_files.sync")

        self.onedrive = onedrive
        self.octoprint_filemanager = octoprint_filemanager

        # Config should give something like below:
        # {
        #    "mode": "onedrive",
        #    "interval": 60,
        #    "onedrive_folder": "...",
        #    "octoprint_folder": "OneDrive",
        #    "max_depth": 4,
        # }

        if callable(config):
            self.config = config
        else:
            self.config = lambda: config

        self.sync_condition = sync_condition
        self.on_sync_start = on_sync_start
        self.on_sync_end = on_sync_end

        self.interrupt = threading.Event()
        self.finished = False

        self.daemon = True

    def stop(self):
        self.finished = True
        self.interrupt.set()

    def run(self):
        while True:
            # Fetch the latest config
            config = self.config()

            # Wait, but break if we're told to stop
            self.interrupt.wait(config["interval"])

            if self.finished:
                break

            if self.sync_condition():
                if callable(self.on_sync_start):
                    self.on_sync_start()

                run_sync(self.onedrive, self.octoprint_filemanager, config)
                self.interrupt.clear()

                if callable(self.on_sync_end):
                    self.on_sync_end()

    def sync_now(self):
        # Override the interval and sync now
        self.interrupt.set()


def run_sync(onedrive, octoprint_filemanager, config):
    """Run a sync of the files to OneDrive"""
    logger.debug("Starting sync run, mode: %s", config["mode"])
    start_time = time.monotonic()

    max_depth = config["max_depth"]
    mode = config["mode"]
    onedrive_folder = config["onedrive_folder"]
    octoprint_folder = config["octoprint_folder"]

    def recursive_list_onedrive_files(folder_id, current_depth=0, current_path="/"):
        result = {}
        root = onedrive.list_files_and_folders(folder_id)
        for item in root["items"]:
            # Check OneDrive file type is valid/supported by OP server
            if item["type"] == "file" and valid_file_type(item["name"]):
                result[current_path + item["name"]] = {
                    "eTag": item["eTag"],
                    "downloadUrl": item["downloadUrl"],
                }

            elif item["type"] == "folder":
                if current_depth < max_depth:
                    result.update(
                        recursive_list_onedrive_files(
                            item["id"],
                            current_depth + 1,
                            current_path + item["name"] + "/",
                        )
                    )
                else:
                    logger.warning(
                        f"Reached max depth of sub-folders, not going further into {current_path}"
                    )

        return result

    def recursive_list_octoprint_files(data, current_depth=0, current_path="/"):
        result = {}

        for name, item in data.items():
            if item["type"] == "machinecode":
                if "onedrive" in item:
                    # OneDrive metadata set
                    result[current_path + item["name"]] = {
                        "eTag": item["onedrive"].get("eTag", ""),
                        "id": item["onedrive"].get("id", ""),
                    }
                else:
                    # Item was not created by OneDriveFileSync
                    result[current_path + item["name"]] = {}

            elif item["type"] == "folder" and item["children"]:
                result.update(
                    recursive_list_octoprint_files(
                        item["children"],
                        current_depth + 1,
                        current_path + item["name"] + "/",
                    )
                )

        return result

    try:
        octoprint_files = recursive_list_octoprint_files(
            octoprint_filemanager.list_files(
                "local", path=octoprint_folder, recursive=True
            )["local"]
        )
        onedrive_files = recursive_list_onedrive_files(onedrive_folder)
    except Exception as e:
        logger.error("Error while listing files")
        logger.exception(e)
        return

    sync_algorithms = {
        "two": two_way_sync,
        "octoprint": octoprint_sync,
        "onedrive": onedrive_sync,
    }
    actions = {
        "upload": upload_onedrive,
        "download": download_onedrive,
        "delete_octoprint": delete_octoprint,
        "delete_onedrive": delete_onedrive,
    }

    if mode not in sync_algorithms:
        logger.error(f"Invalid sync mode: {mode}")
        return

    sync_result = sync_algorithms[mode](octoprint_files, onedrive_files)

    logger.debug("Sync comparison complete")
    if len(sync_result):
        logger.debug("Sync actions:")
        logger.debug(sync_result)

    # At this point we have a list of actions to perform
    for action in sync_result:
        try:
            if action["action"] == "download":
                download_onedrive(
                    octoprint_filemanager, onedrive, onedrive_folder, action["file"]
                )
            elif action["action"] == "upload":
                upload_onedrive(
                    octoprint_filemanager, onedrive, onedrive_folder, action["file"]
                )
            elif action["action"] == "delete_octoprint":
                delete_octoprint(octoprint_filemanager, action["file"])
            elif action["action"] == "delete_onedrive":
                delete_onedrive(onedrive, onedrive_folder, action["file"])
        except Exception as e:
            logger.error("Error syncing file with OneDrive")
            logger.error(
                "Error on file %s, action %s", action["file"], action["action"]
            )
            logger.exception(e)

    end_time = time.monotonic()
    logger.debug("Sync run finished in %s seconds, next run in maximum of %s seconds", round(end_time - start_time, 2), int(config["interval"]))


def two_way_sync(octoprint_data, onedrive_data):
    """
    Two-way sync algorithm producing a list of actions at the end
    :param octoprint_data: dict of files in OctoPrint
    :param onedrive_data: dict of files in OneDrive

    :return: list of actions to perform
    """
    # If the file exists in OneDrive, but not in OctoPrint, it must be downloaded and metadata applied
    # If the file exists in OneDrive and in OctoPrint, check the metadata
    #   If the metadata exists and is different, download and apply the new metadata  (file modified)
    #   If the metadata doesn't exist, then it should be uploaded to OneDrive and new metadata added  (May never happen)
    # If the file exists in OctoPrint, but not OneDrive, check the metadata
    #   If the metadata exists, then the file was deleted from OneDrive and should be deleted from OctoPrint
    #   If the metadata doesn't exist, then it should be uploaded to OneDrive and new metadata added

    actions = []
    # Take a copy of octoprint data so we can remove items as we go
    octoprint_files_remaining = copy.deepcopy(octoprint_data)
    for od_file_name, od_file_data in onedrive_data.items():

        if od_file_name not in octoprint_data:
            # Exists in OneDrive, not OctoPrint, so download
            actions.append({"action": "download", "file": od_file_name})
        else:
            octoprint_files_remaining.pop(od_file_name)
            # Exists in both, check metadata
            op_file_data = octoprint_data[od_file_name]
            if "eTag" in op_file_data and op_file_data["eTag"] != od_file_data["eTag"]:
                # Metadata exists and is different, download (file modified in OneDrive)
                actions.append({"action": "download", "file": od_file_name})
            else:
                # Metadata doesn't exist, upload (file overwritten in OP)
                actions.append({"action": "upload", "file": od_file_name})

    for op_file_name, op_file_data in octoprint_files_remaining.items():
        if "eTag" in op_file_data:
            # Metadata exists, delete from OP (was deleted from OD)
            actions.append({"action": "delete_octoprint", "file": op_file_name})
        else:
            # Metadata doesn't exist, upload (file added in OP)
            actions.append({"action": "upload", "file": op_file_name})

    return actions


def octoprint_sync(octoprint_data, onedrive_data):
    """
    OctoPrint => OneDrive one way sync algorithm producing a list of actions at the end

    :param octoprint_data: dict of files in OctoPrint
    :param onedrive_data: dict of files in OneDrive

    :return: list of actions to perform
    """
    # If the file exists in OneDrive and in OctoPrint, check the metadata
    #   If the metadata is different, then the file was modified in OctoPrint and should be uploaded to OneDrive
    # If the file exists in OneDrive, but not in OctoPrint, it must be deleted from OneDrive
    # If the file exists in OctoPrint, but not OneDrive it should be uploaded to OneDrive
    # NEVER download from OneDrive

    actions = []
    for od_file_name, od_file_data in onedrive_data.items():

        if od_file_name in octoprint_data:
            op_file_data = octoprint_data[od_file_name]
            if "eTag" in op_file_data and op_file_data["eTag"] == od_file_data["eTag"]:
                # Metadata exists and is the same, ignore
                continue
            else:
                # Something is different, upload
                actions.append({"action": "upload", "file": od_file_name})
        else:
            # File exists in OD, but not OP, delete
            actions.append({"action": "delete_onedrive", "file": od_file_name})

    for op_file_name, op_file_data in octoprint_data.items():
        if op_file_name not in onedrive_data:
            # File exists in OP, but not OD, upload
            actions.append({"action": "upload", "file": op_file_name})

    return actions


def onedrive_sync(octoprint_data, onedrive_data):
    """
    OneDrive => OctoPrint one way sync algorithm producing a list of actions at the end

    :param octoprint_data: dict of files in OctoPrint
    :param onedrive_data: dict of files in OneDrive

    :return: list of actions to perform
    """
    # If the file exists in OneDrive and in OctoPrint, check the metadata
    #   If the metadata is different, download and apply the new metadata  (file modified)
    # If the file exists in OneDrive, but not in OctoPrint, it must be downloaded and metadata applied
    # If the file exists in OctoPrint, but not OneDrive, check the metadata
    #   If the metadata exists, then the file was deleted from OneDrive and should be deleted from OctoPrint
    # NEVER upload to OneDrive

    actions = []
    for od_file_name, od_file_data in onedrive_data.items():

        if od_file_name in octoprint_data:
            op_file_data = octoprint_data[od_file_name]
            if "eTag" in op_file_data and op_file_data["eTag"] == od_file_data["eTag"]:
                # Metadata exists and is the same, ignore
                continue
            else:
                # Something is different, download
                actions.append({"action": "download", "file": od_file_name})
        else:
            # File exists in OD, but not OP, download
            actions.append({"action": "download", "file": od_file_name})

    for op_file_name, op_file_data in octoprint_data.items():
        if op_file_name not in onedrive_data:
            if "eTag" in op_file_data:
                # File exists in OP, but not OD (and it was in OD at some point), delete
                actions.append({"action": "delete_octoprint", "file": op_file_name})
            # Otherwise ignore the file

    return actions


def download_onedrive(
    op_filemanager: octoprint.filemanager.FileManager, onedrive: octo_onedrive.onedrive.OneDriveComm, folder_id, filename
):
    logger.debug("Downloading file from OneDrive: %s", filename)

    file_info = onedrive.file_info(root=folder_id, name=filename)
    if "error" in file_info:
        # Abort!
        logger.error("Error fetching file data, skipping (%s)", file_info["error"])
        return

    file_etag, file_id = file_info.get("eTag", ""), file_info.get("id", "")

    temp_path = onedrive.download_file(folder_id, filename)["path"]

    # Do all the long processing to add the file
    new_file_path = pathlib.PurePath(filename[1:])
    file = DiskFileWrapper(new_file_path.name, temp_path)
    future_full_path_in_storage = op_filemanager.path_in_storage(
        FileDestinations.LOCAL,
        str("OneDrive" / new_file_path),
    )

    # TODO check that we are not overwriting something already printing?
    try:
        added_file = op_filemanager.add_file(
            FileDestinations.LOCAL,
            future_full_path_in_storage,
            file,
            allow_overwrite=True,
        )
    except octoprint.filemanager.storage.StorageError as e:
        logger.error("Error adding file to storage, skipping (%s)", e)
        return

    # Apply metadata to the file
    op_filemanager.set_additional_metadata(
        FileDestinations.LOCAL,
        future_full_path_in_storage,
        "onedrive",
        {"eTag": file_etag, "id": file_id},
        overwrite=True,
    )

    if os.path.exists(temp_path):
        print("File still exists - it shouldn't!")


def upload_onedrive(
    op_filemanager: octoprint.filemanager.FileManager, onedrive: octo_onedrive.onedrive.OneDriveComm, folder_id, filename
):
    logger.debug("Uploading file to OneDrive: %s", filename)

    # Get the file from OctoPrint
    file_path = op_filemanager.path_on_disk(FileDestinations.LOCAL, f"OneDrive/{filename}")

    def on_upload_progress(progress):
        logger.debug("Upload progress: %s", progress)

    def on_upload_complete():
        logger.debug("Upload complete")

    def on_upload_error(error):
        logger.error("Upload error: %s", error)

    # Upload the file
    result = onedrive.upload_file(
        filename,
        file_path,
        folder_id,
        on_upload_progress,
        on_upload_complete,
        on_upload_error,
    )

    logger.debug("File uploaded successfully")

    # Update the metadata
    op_filemanager.set_additional_metadata(
        FileDestinations.LOCAL,
        f"OneDrive/{filename}",
        "onedrive",
        {"eTag": result["eTag"], "id": result["id"]},
        overwrite=True,
    )

    # Hopefully that means all is good?
    logger.debug("File metadata updated successfully")


def delete_octoprint(
    op_filemanager: octoprint.filemanager.FileManager, filename
):
    logger.debug("Deleting file from OctoPrint: %s", filename)

    try:
        op_filemanager.remove_file(FileDestinations.LOCAL, f"OneDrive/{filename}")
    except octoprint.filemanager.storage.StorageError as e:
        logger.error("Error deleting file from storage, skipping (%s)", e)


def delete_onedrive(
    onedrive: octo_onedrive.onedrive.OneDriveComm, folder_id,
    filename
):
    logger.debug("Deleting file from OneDrive: %s", filename)

    try:
        result = onedrive.delete_file(folder_id, filename)
    except Exception as e:
        logger.error("Error deleting file from OneDrive, skipping (%s)", e)
        return

    if type(result) == dict and "error" in result:
        logger.error("Error deleting file from OneDrive, skipping (%s)", result["error"])
        return
