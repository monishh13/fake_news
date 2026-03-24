chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "aivera-analyze",
        title: "Analyze with AIVera",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "aivera-analyze" && info.selectionText) {
        // Store the selected text for the popup to pick up
        chrome.storage.local.set({ aiveraPendingText: info.selectionText }, () => {
            // Manifest V3 does not allow opening the action popup programmatically,
            // so we open popup.html as a floating chrome window instead.
            chrome.windows.create({
                url: chrome.runtime.getURL('popup.html'),
                type: 'popup',
                width: 420,
                height: 620,
                focused: true
            });
        });
    }
});
