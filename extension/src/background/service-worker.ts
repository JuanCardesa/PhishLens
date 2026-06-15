chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    phishlensInstalledAt: new Date().toISOString(),
  });
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "PHISHLENS_PING") {
    sendResponse({ ok: true });
  }
  return false;
});
