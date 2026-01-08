// Content script to extract links from Google search results
(() => {
  const links = Array.from(document.querySelectorAll('a'))
    .map(a => a.href)
    .filter(href => href && href.startsWith('http') && !href.includes('google.com'));
  chrome.runtime.sendMessage({ type: 'EXTRACTED_LINKS', links });
})();
