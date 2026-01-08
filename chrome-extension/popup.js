
document.getElementById('open-dashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
});

document.getElementById('import-links-google').addEventListener('click', () => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    const tab = tabs[0];
    if (!tab || !tab.url.includes('google.com/search')) {
      alert('Please focus a Google search results tab.');
      return;
    }
    chrome.scripting.executeScript({
      target: {tabId: tab.id},
      files: ['content.js']
    });
    window.close();
  });
});
