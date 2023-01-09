import * as React from "react"
import copy from "copy-to-clipboard"

export default function CopyButton({ text, content }) {
    const [copied, setCopied] = React.useState(false)
    const [copyError, setCopyError] = React.useState(false)

    const performCopy = async (text) => {
        setCopyError(false)
        if (!navigator?.clipboard) {
            return copy(text)
        }

        try {
            await navigator.clipboard.writeText(text)
            return true
        } catch (error) {
            console.warn("Copy failed", error)
            return false
        }
    }

    const doCopy = () => {
        performCopy(content).then((result) => {
            if (result) {
                setCopied(true)
                setTimeout(() => setCopied(false), 5000)
            } else {
                setCopyError(true)
            }
        })
    }

    const icon = copied ? "fa-check" : "fa-copy"

    return (
        <button className={"btn btn-mini"} onClick={doCopy}>
            <i className={"fas fa-fw " + (copyError ? "fa-times" : icon)} />{" "}
            {text}
        </button>
    )
}
