document.getElementById('uploadBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = 'Loading CSV...';

  try {
    // Read CSV from parent directory
    const csvPath = '../whatnot_import.csv';
    const response = await fetch(csvPath);
    if (!response.ok) throw new Error('CSV not found');

    const csvText = await response.text();
    statusDiv.textContent = 'Navigating to Whatnot...';

    // Inject the upload script into the active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.tabs.sendMessage(tab.id, {
      action: 'upload',
      csv: csvText
    }, (response) => {
      if (chrome.runtime.lastError) {
        statusDiv.textContent = '❌ Not on Whatnot.com';
      } else {
        statusDiv.textContent = response?.status || 'Check Whatnot...';
      }
    });
  } catch (e) {
    statusDiv.textContent = '❌ Error: ' + e.message;
  }
});
