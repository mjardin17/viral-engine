chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'upload') {
    uploadCSV(request.csv, sendResponse);
  }
});

async function uploadCSV(csvText, sendResponse) {
  try {
    // Check if we're on the import page
    if (!window.location.href.includes('whatnot.com')) {
      sendResponse({ status: '❌ Not on Whatnot.com' });
      return;
    }

    // Create a Blob from the CSV text
    const blob = new Blob([csvText], { type: 'text/csv' });
    const file = new File([blob], 'whatnot_import.csv', { type: 'text/csv' });

    // Find the file input on the page
    const fileInputs = document.querySelectorAll('input[type="file"]');

    if (fileInputs.length === 0) {
      sendResponse({ status: '⚠️  No file input found. Make sure you\'re on the import page.' });
      return;
    }

    // Use the first file input
    const fileInput = fileInputs[0];
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Trigger change event
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));

    // Wait a bit for the upload to start
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Look for an import/submit button and click it
    const buttons = document.querySelectorAll('button');
    let clicked = false;

    for (let btn of buttons) {
      if (btn.textContent.toLowerCase().includes('import') ||
          btn.textContent.toLowerCase().includes('upload') ||
          btn.textContent.toLowerCase().includes('submit')) {
        btn.click();
        clicked = true;
        break;
      }
    }

    if (clicked) {
      sendResponse({ status: '✅ Upload started! Check Whatnot for results.' });
    } else {
      sendResponse({ status: '⚠️  CSV loaded but no submit button found. Click import manually.' });
    }
  } catch (e) {
    sendResponse({ status: '❌ Error: ' + e.message });
  }
}
