class GridManager {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.items = new Map();
        this.rawHtmlMap = new Map();
        this.normalizedHtmlMap = new Map();
        this.statusMap = new Map();
    }

    setModels(models) {
        /**
         * Initialize the grid with placeholders for expected models
         */
        this.container.innerHTML = '';
        this.items.clear();
        this.rawHtmlMap.clear();
        this.normalizedHtmlMap.clear();
        this.statusMap.clear();

        for (const modelName of models) {
            const item = this.createGridItem(modelName, null);
            this.container.appendChild(item);
            this.items.set(modelName, item);
        }
    }

    updateVisualization(modelName, html, rawHtml, status) {
        /**
         * Update a specific model's visualization
         */
        if (!this.items.has(modelName)) {
            console.warn(`Ignoring visualization update for unknown model '${modelName}'`)
            return;
        }
        const item = this.items.get(modelName);
        const iframe = item.querySelector('iframe');
        if (iframe) {
            iframe.srcdoc = html || this.getLoadingPlaceholderHtml();
        }
        if (rawHtml != null) {
            this.rawHtmlMap.set(modelName, rawHtml);
        }
        this.normalizedHtmlMap.set(modelName, html);
        if (status) {
            this.updateStatus(modelName, status);
        }
    }

    updateStatus(modelName, status) {
        /**
         * Update the status indicator for a model
         */
        if (!this.items.has(modelName)) return;
        this.statusMap.set(modelName, status);

        const item = this.items.get(modelName);
        const indicator = item.querySelector('.status-indicator');
        if (!indicator) return;

        indicator.className = 'status-indicator';
        indicator.removeAttribute('title');

        if (status === 'generating') {
            indicator.className = 'status-indicator generating';
        } else if (status === 'outdated') {
            indicator.className = 'status-indicator outdated';
            indicator.textContent = '\u26A0';
            indicator.setAttribute('title', 'Visualization is outdated \u2014 generated from previous weather data');
            return;
        }
        indicator.textContent = '';
    }

    markAllOutdated() {
        /**
         * Mark all models as outdated
         */
        for (const modelName of this.items.keys()) {
            this.updateStatus(modelName, 'outdated');
        }
    }

    createGridItem(modelName, html) {
        const item = document.createElement('div');
        item.className = 'grid-item';
        item.dataset.model = modelName;

        const header = document.createElement('div');
        header.className = 'grid-item-header';

        const title = document.createElement('span');
        title.className = 'grid-item-title';
        title.textContent = modelName;

        const actions = document.createElement('span');
        actions.className = 'header-actions';

        const statusIndicator = document.createElement('span');
        statusIndicator.className = 'status-indicator';

        const expandBtn = document.createElement('button');
        expandBtn.className = 'expand-btn';
        expandBtn.setAttribute('aria-label', `Expand ${modelName} visualization`);
        expandBtn.setAttribute('title', 'Expand');
        expandBtn.textContent = '\u26F6';

        actions.appendChild(statusIndicator);
        actions.appendChild(expandBtn);

        header.appendChild(title);
        header.appendChild(actions);

        const iframe = document.createElement('iframe');
        iframe.srcdoc = html || this.getLoadingPlaceholderHtml();

        item.appendChild(header);
        item.appendChild(iframe);

        return item;
    }

    getNormalizedHtmlContent(modelName) {
        return this.normalizedHtmlMap.get(modelName) || null;
    }

    getRawHtmlContent(modelName) {
        return this.rawHtmlMap.get(modelName) || null;
    }

    getLoadingPlaceholderHtml() {
        // Placeholder loading HTML
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                    }
                    .loader {
                        text-align: center;
                    }
                    .spinner {
                        border: 4px solid rgba(255, 255, 255, 0.3);
                        border-radius: 50%;
                        border-top: 4px solid white;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 1rem;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </head>
            <body>
                <div class="loader">
                    <div class="spinner"></div>
                    <p>Generating visualization...</p>
                </div>
            </body>
            </html>
        `;
    }
}
