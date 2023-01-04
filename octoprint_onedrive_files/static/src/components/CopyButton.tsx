import * as React from "react"


export default function CopyButton ({text, content}) {
    const [copied, setCopied] = React.useState(false)
    const [copyError, setCopyError] = React.useState(false)

    const copy = async text => {
        setCopyError(false)
        if (!navigator?.clipboard) {
            console.warn('Clipboard not supported')
            return false
        }

        // Try to save to clipboard then save it in the state if worked
        try {
            await navigator.clipboard.writeText(text)
            return true
        } catch (error) {
            console.warn('Copy failed', error)
            return false
        }
    }

    const doCopy = () => {
        copy(content).then(result => {
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
        <button className={"btn btn-mini"} onClick={doCopy} >
           <i className={"fas fa-fw " + (copyError ? "fa-times" : icon)} />
           {" "}{text}
       </button>
    )
}
