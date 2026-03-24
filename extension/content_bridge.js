/**
 * Content Bridge Script (runs in ISOLATED world — has access to chrome APIs)
 *
 * Protocol:
 *  1. React app mounts and sends  window.postMessage({ type: 'AIVERA_READY' })
 *  2. This script reads the stored report from chrome.storage and replies with
 *     window.postMessage({ type: 'AIVERA_REPORT', data: <fullResult> })
 *  3. React receives the data and renders it — no DB lookup needed.
 *
 * Only activates when the page URL contains ?report=... (opened from extension).
 */

const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has('report')) {
    chrome.storage.local.get('aivera_pending_report', (result) => {
        const reportData = result.aivera_pending_report;
        if (!reportData) return;

        // Clean up so it doesn't persist on refresh
        chrome.storage.local.remove('aivera_pending_report');

        // Wait for the React app to signal it is mounted and ready
        const onMessage = (event) => {
            if (event.source === window && event.data && event.data.type === 'AIVERA_READY') {
                window.removeEventListener('message', onMessage);
                // Respond with the full analysis result
                window.postMessage({ type: 'AIVERA_REPORT', data: reportData }, '*');
            }
        };
        window.addEventListener('message', onMessage);
    });
}
