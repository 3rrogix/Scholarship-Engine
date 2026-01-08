// Content script to extract links from Google search results
// Only runs when injected by the dashboard's "Import links" button
if (window.location.hostname === 'www.google.com' && window.location.pathname === '/search') {
  const links = Array.from(document.querySelectorAll('a'))
    .map(a => a.href)
    .filter(href => href && href.startsWith('http') && !href.includes('google.com'));
  chrome.runtime.sendMessage({ type: 'EXTRACTED_LINKS', links });
}
