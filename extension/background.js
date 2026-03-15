chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "aivera-analyze",
        title: "Analyze with AIVera",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "aivera-analyze" && info.selectionText) {
        // Store the selected text
        chrome.storage.local.set({ aiveraPendingText: info.selectionText }, () => {
            // Open the extension popup or a new tab depending on Chrome limitations
            // Manifest V3 limits opening popups programmatically from background scripts.
            // As a workaround, we inject a script to show a small toast, or ask the user to click the icon.
            chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: (text) => {
                    alert(`AIVera: Sent "${text.substring(0, 30)}..." to analysis.\nPlease click the AIVera extension icon in your toolbar to view results.`);
                },
                args: [info.selectionText]
            });
        });
    }
});
