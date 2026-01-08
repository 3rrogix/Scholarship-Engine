// Dashboard logic for Gemini API key, links, and resume

document.addEventListener('DOMContentLoaded', () => {
  // API Key
  const apiKeyInput = document.getElementById('api-key');
  const apiKeyForm = document.getElementById('api-key-form');
  const apiKeyStatus = document.getElementById('api-key-status');

  // Load API key (hidden)
  chrome.storage.local.get(['geminiApiKey'], (result) => {
    if (result.geminiApiKey) {
      apiKeyInput.value = result.geminiApiKey;
      apiKeyInput.type = 'password';
      apiKeyStatus.textContent = 'API key loaded (hidden)';
    }
  });

  apiKeyForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const key = apiKeyInput.value.trim();
    if (key) {
      chrome.storage.local.set({ geminiApiKey: key }, () => {
        apiKeyStatus.textContent = 'API key saved!';
        apiKeyInput.type = 'password';
      });
    }
  });

  // Links
  const linksList = document.getElementById('links-list');
  const addLinkForm = document.getElementById('add-link-form');
  const newLinkInput = document.getElementById('new-link');

  function renderLinks(links) {
    linksList.innerHTML = '';
    links.forEach((link, idx) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = link;
      a.textContent = link;
      a.target = '_blank';
      li.appendChild(a);
      const delBtn = document.createElement('button');
      delBtn.textContent = 'Remove';
      delBtn.addEventListener('click', () => {
        links.splice(idx, 1);
        chrome.storage.local.set({ scholarshipLinks: links }, () => renderLinks(links));
      });
      li.appendChild(delBtn);
      linksList.appendChild(li);
    });
  }

  function loadLinks() {
    chrome.storage.local.get(['scholarshipLinks'], (result) => {
      renderLinks(result.scholarshipLinks || []);
    });
  }
  loadLinks();

  addLinkForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = newLinkInput.value.trim();
    if (url) {
      chrome.storage.local.get(['scholarshipLinks'], (result) => {
        const links = result.scholarshipLinks || [];
        if (!links.includes(url)) {
          links.push(url);
          chrome.storage.local.set({ scholarshipLinks: links }, () => {
            renderLinks(links);
            newLinkInput.value = '';
          });
        }
      });
    }
  });

  // Resume
  const resumeTextarea = document.getElementById('resume');
  const saveResumeBtn = document.getElementById('save-resume');
  const resumeStatus = document.getElementById('resume-status');

  chrome.storage.local.get(['resumeText'], (result) => {
    if (result.resumeText) {
      resumeTextarea.value = result.resumeText;
      resumeStatus.textContent = 'Resume loaded.';
    }
  });

  saveResumeBtn.addEventListener('click', () => {
    const text = resumeTextarea.value.trim();
    chrome.storage.local.set({ resumeText: text }, () => {
      resumeStatus.textContent = 'Resume saved!';
      setTimeout(() => resumeStatus.textContent = '', 2000);
    });
  });

  // Scholarship Search
  const searchForm = document.getElementById('search-form');
  const searchQueryInput = document.getElementById('search-query');
  const searchStatus = document.getElementById('search-status');

  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = searchQueryInput.value.trim();
    if (!query) return;
    searchStatus.textContent = 'Searching...';
    // Use Google Custom Search API or fallback to Bing as fetch (no direct Google scraping in browser)
    // For demo, use Bing Web Search API (user must provide their own key if needed)
    // Here, we just open a Google search tab for the query and let the user handle it
    const googleUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    chrome.tabs.create({ url: googleUrl });
    searchStatus.textContent = 'Opened Google search in new tab. Please review and add links manually.';
  });

  // Import links from Google search tab
  const importLinksBtn = document.getElementById('import-links');
  importLinksBtn.addEventListener('click', async () => {
    searchStatus.textContent = 'Importing links from Google search tab...';
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url.includes('google.com/search')) {
        searchStatus.textContent = 'Please focus a Google search results tab.';
        return;
      }
      chrome.scripting.executeScript({
        target: {tabId: tab.id},
        files: ['content.js']
      });
    });
  });

  // Listen for extracted links from content script
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'EXTRACTED_LINKS') {
      const links = msg.links || [];
      if (links.length === 0) {
        searchStatus.textContent = 'No links found.';
        return;
      }
      chrome.storage.local.get(['scholarshipLinks'], (result) => {
        const existing = result.scholarshipLinks || [];
        const newLinks = links.filter(l => !existing.includes(l));
        const updated = existing.concat(newLinks);
        chrome.storage.local.set({ scholarshipLinks: updated }, () => {
          renderLinks(updated);
          searchStatus.textContent = `Imported ${newLinks.length} new links.`;
        });
      });
    }
  });
});
