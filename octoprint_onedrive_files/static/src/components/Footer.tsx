import * as React from "react"

export default function Footer () {
  return (
    <>
      <hr />
      <p>
        OneDrive File Sync by{" "}
        <a href={"https://github.com/cp2004"} target={"_blank"} rel="noreferrer">
          Charlie Powell
        </a>
        {" | "}<i className={"fas fa-tag text-success"} />
        <a href={"https://github.com/cp2004/OctoPrint-OneDriveFilesSync/releases"} target={"_blank"} rel={"noreferrer"}> Release notes</a>
      </p>
    </>
  )
}
