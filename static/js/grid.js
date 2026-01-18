class GridManager {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.items = new Map();
    }

    setModels(models) {
        /**
         * Initialize the grid with placeholders for expected models
         */
        this.container.innerHTML = '';
        this.items.clear();

        for (const modelName of models) {
            const item = this.createGridItem(modelName, null);
            this.container.appendChild(item);
            this.items.set(modelName, item);
        }
    }

    updateVisualization(modelName, html) {
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

        const expandBtn = document.createElement('button');
        expandBtn.className = 'expand-btn';
        expandBtn.setAttribute('aria-label', `Expand ${modelName} visualization`);
        expandBtn.setAttribute('title', 'Expand');
        expandBtn.textContent = '\u26F6';

        header.appendChild(title);
        header.appendChild(expandBtn);

        const iframe = document.createElement('iframe');
        iframe.srcdoc = html || this.getLoadingPlaceholderHtml();

        item.appendChild(header);
        item.appendChild(iframe);

        return item;
    }

    getVisualizationContent(modelName) {
        /**
         * Get the current srcdoc content for a model's visualization
         */
        if (!this.items.has(modelName)) {
            return null;
        }
        const item = this.items.get(modelName);
        const iframe = item.querySelector('iframe');
        return iframe ? iframe.srcdoc : null;
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
