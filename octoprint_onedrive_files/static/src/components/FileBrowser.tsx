import * as React from "react"
import { useQuery } from "@tanstack/react-query"

//@ts-ignore:next-line
const OctoPrint = window.OctoPrint
const PLUGIN_ID = "onedrive_files"

export default function FileBrowser() {
    const [active, setActive] = React.useState<boolean>(false)
    const [currentFolder, setCurrentFolder] = React.useState<string>("root")

    const [history, setHistory] = React.useState<string[]>([])
    const [historyPos, setHistoryPos] = React.useState<number>(0)

    const fetchFiles = (itemId: string = "root") => {
        if (itemId === "root") {
            return OctoPrint.simpleApiCommand(PLUGIN_ID, "folders")
        } else {
            return OctoPrint.simpleApiCommand(PLUGIN_ID, "foldersById", {
                id: itemId,
            })
        }
    }

    const {
        data,
        isFetching,
        error: folderQueryError,
        refetch: refetchFolders,
    } = useQuery(["folders", currentFolder], () => fetchFiles(currentFolder), {
        enabled: active,
    })

    const {
        data: configData,
        isFetching: configDataFetching,
        refetch: refetchConfig,
    } = useQuery(["accounts"], () => {
        return OctoPrint.simpleApiGet(PLUGIN_ID)
    })

    const handleSelectFolder = (target) => {
        setHistory((prevState) => prevState.concat([currentFolder]))
        setCurrentFolder(target)
        setHistoryPos((prevState) => prevState + 1)
    }

    const handleBack = () => {
        if (history.length >= 0 && historyPos > 0) {
            const newHistoryPos = historyPos - 1
            const newFolder = history[newHistoryPos]
            setHistoryPos(newHistoryPos)
            setCurrentFolder(newFolder)
            setHistory((prevState) => prevState.slice(0, newHistoryPos))
        }
    }

    const handleActivateFolder = (folder) => {
        OctoPrint.simpleApiCommand(PLUGIN_ID, "setFolder", {
            id: folder.id,
            path: folder.path,
        }).done(() => refetchConfig())
    }

    const files = data?.folders
        ? data.folders.map((folder) => (
              <tr key={folder.id}>
                  <td>
                      {folder.childCount > 0 ? (
                          <a
                              onClick={() => handleSelectFolder(folder.id)}
                              style={{ cursor: "pointer" }}
                          >
                              <i className={"far fa-folder-open"} />{" "}
                              {folder.name}
                          </a>
                      ) : (
                          <span>
                              <i className={"far fa-folder-open"} />{" "}
                              {folder.name}
                          </span>
                      )}
                  </td>
                  <td>
                      <button
                          className={"btn btn-primary btn-mini"}
                          onClick={() => handleActivateFolder(folder)}
                      >
                          Set sync folder
                      </button>
                  </td>
              </tr>
          ))
        : []

    const hasError = folderQueryError || data?.error
    const loading = isFetching || configDataFetching // && active

    return (
        <>
            <h5>Sync Folder</h5>
            <p>
                {configDataFetching ? (
                    <span>
                        <i className={"fas fa-spin fa-spinner"} /> Loading...
                    </span>
                ) : (
                    <span>
                        Currently configured sync folder:{" "}
                        {configData?.folder.path ? (
                            <code>{configData.folder.path}</code>
                        ) : (
                            "None"
                        )}
                    </span>
                )}
            </p>
            <p>
                Files will be synced between this folder in OneDrive and the
                'OneDrive' folder in OctoPrint.
            </p>
            <div className={"row-fluid"}>
                {configData?.folder.path && (
                    <button
                        className={"btn btn-primary"}
                        style={{ marginRight: "5px" }}
                        onClick={() =>
                            handleActivateFolder({ id: "", path: "" })
                        }
                    >
                        <i
                            className={
                                "fa-fw " +
                                (loading
                                    ? "fas fa-spin fa-spinner"
                                    : "fas fa-times")
                            }
                        />{" "}
                        Clear folder
                    </button>
                )}
                {!active && (
                    <button
                        className={"btn btn-primary"}
                        onClick={() => setActive(true)}
                    >
                        <i
                            className={
                                "fa-fw " +
                                (isFetching
                                    ? "fas fa-spin fa-spinner"
                                    : "far fa-folder-open")
                            }
                        />{" "}
                        Change folder
                    </button>
                )}
                {active && (
                    <button
                        className={"btn btn-primary"}
                        onClick={() => refetchFolders()}
                    >
                        <i
                            className={
                                "fa-fw fas fa-sync " +
                                (isFetching ? "fa-spin" : "")
                            }
                        />{" "}
                        {hasError ? "Retry" : "Refresh"}
                    </button>
                )}
            </div>
            {hasError && (
                <div className={"alert alert-error"}>
                    <i className={"fas fa-times text-error"} />
                    <strong> Error:</strong>
                    {typeof data.error === "string"
                        ? data.error
                        : "Unknown error. Check octoprint.log for details."}
                </div>
            )}
            {active && (
                <table className={"table"}>
                    <thead>
                        <tr>
                            <th>
                                Folder name{" "}
                                {loading && (
                                    <i className={"fas fa-spin fa-spinner"} />
                                )}{" "}
                            </th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {historyPos > 0 && (
                            <tr>
                                <td>
                                    <span
                                        onClick={handleBack}
                                        style={{ cursor: "pointer" }}
                                    >
                                        <i className={"fas fa-arrow-left"} />{" "}
                                        Back
                                    </span>
                                </td>
                                <td />
                            </tr>
                        )}
                        {files.length ? (
                            files
                        ) : (
                            <>
                                {!loading && !hasError && (
                                    <tr>
                                        <td>
                                            <i className={"fas fa-times"} /> No
                                            sub-folders found
                                        </td>
                                    </tr>
                                )}
                            </>
                        )}
                    </tbody>
                </table>
            )}
        </>
    )
}
