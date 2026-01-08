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

  // Helper to shorten URLs
  function shortenUrl(url) {
    try {
      let u = url.replace(/^https?:\/\//, '').replace(/^www\./, '');
      u = u.replace(/\.[a-z]{2,6}([\/\?#].*)?$/, ''); // Remove domain ending
      return u.length > 40 ? u.slice(0, 37) + '...' : u;
    } catch {
      return url;
    }
  }

  // Render links with status, color, saved state, and review button
  function renderLinks(links) {
    linksList.innerHTML = '';
    links.forEach((linkObj, idx) => {
      // Support old format (string) and new format (object)
      let link = typeof linkObj === 'string' ? linkObj : linkObj.url;
      let status = linkObj.status || '';
      let saved = linkObj.saved || false;
      let colorClass = '';
      if (status === 'open') colorClass = 'link-status-open';
      else if (status === 'closed') colorClass = 'link-status-closed';
      else if (status === 'not found') colorClass = 'link-status-notfound';
      else if (status === 'ad') colorClass = 'link-status-ad';
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = link;
      a.className = 'short-link ' + colorClass + (saved ? ' link-saved' : '');
      a.textContent = shortenUrl(link);
      a.title = link;
      a.target = '_blank';
      li.appendChild(a);
      // Status label
      if (status) {
        const st = document.createElement('span');
        st.textContent = ' [' + status + ']';
        st.className = colorClass;
        li.appendChild(st);
      }
      // Saved toggle
      const saveBtn = document.createElement('button');
      saveBtn.textContent = saved ? 'Unsave' : 'Save';
      saveBtn.onclick = () => {
        links[idx].saved = !saved;
        chrome.storage.local.set({ scholarshipLinks: links }, () => renderLinks(links));
      };
      li.appendChild(saveBtn);
      // Review button
      const reviewBtn = document.createElement('button');
      reviewBtn.textContent = 'Review with Gemini';
      reviewBtn.onclick = () => reviewLinkWithGemini(link, idx);
      li.appendChild(reviewBtn);
      // Remove button
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

  // Update loadLinks to support new format
  function loadLinks() {
    chrome.storage.local.get(['scholarshipLinks'], (result) => {
      let links = result.scholarshipLinks || [];
      // Convert old string format to object
      links = links.map(l => typeof l === 'string' ? { url: l } : l);
      chrome.storage.local.set({ scholarshipLinks: links }, () => renderLinks(links));
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

  // Review link with Gemini
  async function reviewLinkWithGemini(link, idx, cb) {
    searchStatus.textContent = `Reviewing: ${link}`;
    chrome.storage.local.get(['geminiApiKey', 'scholarshipLinks'], (result) => {
      const apiKey = result.geminiApiKey;
      if (!apiKey) {
        searchStatus.textContent = 'Gemini API key not set.';
        if (cb) cb();
        return;
      }
      chrome.tabs.create({ url: link, active: false }, (tab) => {
        const tabId = tab.id;
        function handleTabUpdated(updatedTabId, info) {
          if (updatedTabId === tabId && info.status === 'complete') {
            chrome.scripting.executeScript({
              target: { tabId },
              func: () => document.body.innerText.slice(0, 5000)
            }, (results) => {
              const pageText = results && results[0] && results[0].result;
              // Call Gemini API
              fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=' + apiKey, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  contents: [{ parts: [{ text: `Classify this page as a scholarship opportunity (open) if the application seems to be open, closed if you see the scholarship is past its due date, not found if you can't find a place to apply for the scholarship, or ad. If the scholarship is only available to students of a specific college or university, classify it as an ad. Respond with only one of: open, closed, not found, ad.\n\n${pageText}` }] }]
                })
              })
                .then(r => r.json())
                .then(data => {
                  let status = 'not found';
                  try {
                    const txt = data.candidates[0].content.parts[0].text.toLowerCase();
                    if (txt.includes('open')) status = 'open';
                    else if (txt.includes('closed')) status = 'closed';
                    else if (txt.includes('ad')) status = 'ad';
                    else status = 'not found';
                  } catch {}
                  chrome.storage.local.get(['scholarshipLinks'], (r2) => {
                    const links = r2.scholarshipLinks || [];
                    links[idx].status = status;
                    chrome.storage.local.set({ scholarshipLinks: links }, () => renderLinks(links));
                  });
                  searchStatus.textContent = `Reviewed: ${link} (${status})`;
                  chrome.tabs.remove(tabId);
                  chrome.tabs.onUpdated.removeListener(handleTabUpdated);
                  if (cb) cb();
                })
                .catch(() => {
                  searchStatus.textContent = 'Gemini API error.';
                  chrome.tabs.remove(tabId);
                  chrome.tabs.onUpdated.removeListener(handleTabUpdated);
                  if (cb) cb();
                });
            });
          }
        }
        chrome.tabs.onUpdated.addListener(handleTabUpdated);
      });
    });
  }

  // Review all links with Gemini
  const reviewAllBtn = document.getElementById('review-all');
  reviewAllBtn.addEventListener('click', async () => {
    chrome.storage.local.get(['scholarshipLinks'], (result) => {
      const links = result.scholarshipLinks || [];
      const delayMs = 2500; // 2.5 seconds between requests to avoid rate limits
      function reviewNext(i) {
        if (i >= links.length) {
          searchStatus.textContent = 'All links reviewed.';
          loadLinks();
          return;
        }
        reviewLinkWithGemini(links[i].url, i, () => {
          setTimeout(() => reviewNext(i + 1), delayMs);
        });
      }
      reviewNext(0);
    });
  });
});
