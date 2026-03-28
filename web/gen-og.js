// Extracts OG image from generate-og.html via headless browser approach
// Since we can't run headless Chrome easily, we'll recreate the canvas in Node

const { createCanvas } = (() => {
  try { return require('canvas'); } catch { return { createCanvas: null }; }
})();

const fs = require('fs');
const { execSync } = require('child_process');

// Try using the preview's saved base64 approach
// Fallback: use osascript to open the HTML and trigger download

// Simplest: just open in browser and let user click download
const path = require('path');
const htmlPath = path.resolve(__dirname, 'generate-og.html');

console.log('Opening OG image generator in your browser...');
console.log('Click the "Download PNG" button to save og-image.png');
console.log('Then move it to the web/ folder.');
execSync(`open "${htmlPath}"`);
