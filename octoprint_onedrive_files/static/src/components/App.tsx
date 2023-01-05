import * as React from "react"

import ErrorBoundary from "./ErrorBoundary"
import FileBrowser from "./FileBrowser"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import Auth from "./Auth"

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
        },
    },
})

export default function Index() {
    return (
        <ErrorBoundary onError={OnError}>
            <QueryClientProvider client={queryClient}>
                <ReactQueryDevtools initialIsOpen={false} />
                <App />
            </QueryClientProvider>
        </ErrorBoundary>
    )
}

function OnError() {
    return (
        <>
            <h2 className={"text-error"}>
                There was an error rendering the UI.
            </h2>
            <p>
                {"Please "}
                <a
                    href={
                        "https://github.com/cp2004/OctoPrint-OneDriveFilesSync/issues/new/choose"
                    }
                    target={"_blank"}
                    rel="noreferrer"
                >
                    report this error
                </a>
                , including the full JavaScript console contents in the report.
            </p>
        </>
    )
}

function App() {
    return (
        <>
            <Auth />
            <hr />
            <FileBrowser />
        </>
    )
}
