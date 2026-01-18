const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
const ws = new WeatherWebSocket(wsUrl);
const grid = new GridManager('#grid-container');

// UI Elements
const statusEl = document.getElementById('status');
const timestampTimeEl = document.querySelector('.timestamp-time');
const timestampDateEl = document.querySelector('.timestamp-date');
const infoDialog = document.getElementById('info-dialog');
const promptDisplay = document.getElementById('prompt-display');
const weatherDisplay = document.getElementById('weather-display');
const modelsList = document.getElementById('models-list');

// Current state
let currentConfig = null;
let currentWeather = null;

// WebSocket event handlers
ws.on('status', (status) => {
    statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusEl.className = `status ${status}`;
});

ws.on('config_info', (data) => {
    currentConfig = data;
    grid.setModels(data.models);

    // Update dialog content
    promptDisplay.textContent = data.prompt_template;
    modelsList.innerHTML = data.models.map(m => `<li>${m}</li>`).join('');
});

ws.on('weather_data', (data) => {
    currentWeather = data.weather;
    weatherDisplay.textContent = JSON.stringify(data.weather, null, 2);
    updateTimestamp(data.timestamp);
});

ws.on('visualization_update', (data) => {
    grid.updateVisualization(data.model_name, data.html);
    console.log('Visualization updated for', data.model_name);
});

ws.on('error', (error) => {
    console.error('WebSocket error:', error);
});

// UI event handlers
document.getElementById('info-btn').addEventListener('click', () => {
    infoDialog.showModal();
});

document.getElementById('close-dialog').addEventListener('click', () => {
    infoDialog.close();
});

// Close dialog on backdrop click
infoDialog.addEventListener('click', (e) => {
    if (e.target === infoDialog) {
        infoDialog.close();
    }
});

// Expand dialog elements
const expandDialog = document.getElementById('expand-dialog');
const expandDialogTitle = expandDialog.querySelector('.expand-dialog-title');
const expandDialogIframe = expandDialog.querySelector('.expand-iframe');
const expandCloseBtn = expandDialog.querySelector('.expand-close-btn');

function openExpandedView(modelName) {
    const content = grid.getVisualizationContent(modelName);
    if (content) {
        expandDialogTitle.textContent = modelName;
        expandDialogIframe.srcdoc = content;
        expandDialog.showModal();
    }
}

// Event delegation for grid item expansion
document.getElementById('grid-container').addEventListener('click', (e) => {
    const expandBtn = e.target.closest('.expand-btn');
    const header = e.target.closest('.grid-item-header');

    if (!expandBtn && !header) return;

    const gridItem = e.target.closest('.grid-item');
    if (!gridItem) return;

    const modelName = gridItem.dataset.model;
    openExpandedView(modelName);
});

// Close expand dialog handlers
expandCloseBtn.addEventListener('click', () => {
    expandDialog.close();
});

expandDialog.addEventListener('click', (e) => {
    if (e.target === expandDialog) {
        expandDialog.close();
    }
});

// Clean up iframe when dialog closes
expandDialog.addEventListener('close', () => {
    expandDialogIframe.srcdoc = '';
});

// Helper functions
function updateTimestamp(isoString) {
    const date = new Date(isoString);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    timestampTimeEl.textContent = `${hours}:${minutes}`;
    timestampDateEl.textContent = `${day}.${month}.${year}`;
}

// Initialize
console.log('AI Weather initializing...');
ws.connect();
