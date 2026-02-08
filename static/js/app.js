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

// Theme management
const THEME_KEY = 'theme-preference';
const THEME_CYCLE = ['auto', 'light', 'dark'];
const THEME_ICONS = { auto: '\u25D0', light: '\u2600\uFE0F', dark: '\u263D' };
const THEME_LABELS = { auto: 'Auto', light: 'Light', dark: 'Dark' };
const themeToggle = document.getElementById('theme-toggle');

function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || 'auto';
}

function applyTheme(theme) {
    if (theme === 'light' || theme === 'dark') {
        document.documentElement.setAttribute('data-theme', theme);
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    themeToggle.textContent = THEME_ICONS[theme];
    themeToggle.title = `Theme: ${THEME_LABELS[theme]}`;
}

themeToggle.addEventListener('click', () => {
    const current = getStoredTheme();
    const next = THEME_CYCLE[(THEME_CYCLE.indexOf(current) + 1) % THEME_CYCLE.length];
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
});

applyTheme(getStoredTheme());

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
    grid.markAllOutdated();
});

ws.on('visualization_update', (data) => {
    grid.updateVisualization(data.model_name, data.html, data.raw_html, data.status);
    console.log('Visualization updated for', data.model_name, 'status:', data.status);
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
const codeDisplay = expandDialog.querySelector('.code-display');
const codeTabs = expandDialog.querySelectorAll('.code-tab');

// Code panel state
let expandedModelName = null;
let activeTab = 'normalized';
let highlightedContent = { normalized: null, raw: null };

function updateCodePanel() {
    let sourceHtml;
    if (activeTab === 'normalized') {
        sourceHtml = grid.getNormalizedHtmlContent(expandedModelName);
    } else {
        sourceHtml = grid.getRawHtmlContent(expandedModelName);
    }

    if (!sourceHtml) {
        codeDisplay.textContent = '(No content available)';
        codeDisplay.removeAttribute('data-highlighted');
        return;
    }

    if (highlightedContent[activeTab] === sourceHtml) {
        return;
    }

    codeDisplay.textContent = sourceHtml;
    codeDisplay.removeAttribute('data-highlighted');
    codeDisplay.className = 'code-display language-html';
    hljs.highlightElement(codeDisplay);
    highlightedContent[activeTab] = sourceHtml;
}

function openExpandedView(modelName) {
    const content = grid.getNormalizedHtmlContent(modelName);
    if (!content) return;

    expandedModelName = modelName;
    expandDialogTitle.textContent = modelName;
    expandDialogIframe.srcdoc = content;

    highlightedContent = { normalized: null, raw: null };
    activeTab = 'normalized';
    codeTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === 'normalized');
    });
    updateCodePanel();

    expandDialog.showModal();
}

// Tab switching
codeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        if (tab.dataset.tab === activeTab) return;
        activeTab = tab.dataset.tab;
        codeTabs.forEach(t => {
            t.classList.toggle('active', t.dataset.tab === activeTab);
        });
        updateCodePanel();
    });
});

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

// Clean up iframe and code panel when dialog closes
expandDialog.addEventListener('close', () => {
    expandDialogIframe.srcdoc = '';
    codeDisplay.textContent = '';
    codeDisplay.removeAttribute('data-highlighted');
    expandedModelName = null;
    highlightedContent = { normalized: null, raw: null };
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
