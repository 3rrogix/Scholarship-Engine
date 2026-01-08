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
});
