// ITR Report Viewer - JavaScript Application

const API_BASE = '';  // Same origin
let currentReport = null;
let currentPage = 1;
let totalPages = 1;
let reports = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadReports();
});

// Load all reports from API
async function loadReports() {
    const reportList = document.getElementById('report-list');
    reportList.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading reports...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/reports`);
        if (!response.ok) throw new Error('Failed to load reports');

        reports = await response.json();
        document.getElementById('report-count').textContent = reports.length;

        if (reports.length === 0) {
            reportList.innerHTML = `
                <div class="loading">
                    <p>No reports found. Upload a PDF to get started.</p>
                </div>
            `;
            return;
        }

        reportList.innerHTML = reports.map(report => `
            <div class="report-card fade-in" onclick="selectReport('${report.report_id}')">
                <div class="report-card-title">${report.pdf_filename}</div>
                <div class="report-card-meta">
                    <span class="report-card-badge">
                        <i class="fas fa-calendar"></i>
                        ${report.report_period || 'Unknown'}
                    </span>
                    <span class="report-card-badge">
                        <i class="fas fa-file-alt"></i>
                        ${report.total_pages} pages
                    </span>
                    <span class="report-card-badge">
                        <i class="fas fa-chart-line"></i>
                        ${report.total_series} series
                    </span>
                    <span class="report-card-badge">
                        <i class="fas fa-image"></i>
                        ${report.total_charts} charts
                    </span>
                </div>
            </div>
        `).join('');

        // Auto-select first report
        if (reports.length > 0) {
            selectReport(reports[0].report_id);
        }

    } catch (error) {
        console.error('Error loading reports:', error);
        reportList.innerHTML = `
            <div class="loading">
                <p style="color: var(--color-error);">Error loading reports: ${error.message}</p>
                <button class="btn btn-primary" onclick="loadReports()">Retry</button>
            </div>
        `;
    }
}

// Select a report to view
async function selectReport(reportId) {
    // Update active state
    document.querySelectorAll('.report-card').forEach(card => card.classList.remove('active'));
    event?.target?.closest('.report-card')?.classList.add('active');

    try {
        const response = await fetch(`${API_BASE}/api/reports/${reportId}`);
        if (!response.ok) throw new Error('Failed to load report');

        currentReport = await response.json();
        totalPages = currentReport.metadata?.total_pages || 1;
        currentPage = 1;

        // Update PDF viewer
        updatePDFViewer();

        // Update overview tab
        updateOverview();

        // Update series tab
        updateSeries();

        // Update charts/LLM analysis tab
        updateCharts();

        // Update raw data tab
        document.getElementById('raw-content').textContent =
            JSON.stringify(currentReport, null, 2);

        // Add to AI context
        addAIContext();

    } catch (error) {
        console.error('Error loading report:', error);
        showError('Failed to load report details');
    }
}

// Update PDF viewer
function updatePDFViewer() {
    const pdfViewer = document.getElementById('pdf-viewer');
    const pageInfo = document.getElementById('page-info');

    if (currentReport?.pdf_filename) {
        // Construct PDF URL - assumes PDFs are served from /files/
        const pdfUrl = `${API_BASE}/files/${encodeURIComponent(currentReport.pdf_filename)}#page=${currentPage}`;
        pdfViewer.src = pdfUrl;
    }

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
}

// Page navigation
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        updatePDFViewer();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        updatePDFViewer();
    }
}

// Go to specific page (called from series/chart links)
function goToPage(pageNum) {
    if (pageNum >= 1 && pageNum <= totalPages) {
        currentPage = pageNum;
        updatePDFViewer();

        // Highlight comparison mode
        document.getElementById('comparison-mode').style.display = 'flex';
        setTimeout(() => {
            document.getElementById('comparison-mode').style.display = 'none';
        }, 3000);
    }
}

// Update overview tab
function updateOverview() {
    const content = document.getElementById('overview-content');

    if (!currentReport) {
        content.innerHTML = '<div class="loading"><p>Select a report to view details</p></div>';
        return;
    }

    const metadata = currentReport.metadata || {};
    const seriesCount = currentReport.series_index?.length || 0;

    content.innerHTML = `
        <div class="series-card slide-down">
            <div class="series-header">
                <span class="series-name">${currentReport.pdf_filename}</span>
                <span class="series-sector">${currentReport.report_period || 'Unknown Period'}</span>
            </div>
            <div class="series-content">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 1rem;">
                    <div class="meta-badge" style="padding: 1rem; flex-direction: column; align-items: flex-start;">
                        <span style="font-size: 2rem; font-weight: bold; color: var(--color-primary);">${metadata.total_pages || 0}</span>
                        <span>Pages</span>
                    </div>
                    <div class="meta-badge" style="padding: 1rem; flex-direction: column; align-items: flex-start;">
                        <span style="font-size: 2rem; font-weight: bold; color: var(--color-success);">${seriesCount}</span>
                        <span>Series</span>
                    </div>
                    <div class="meta-badge" style="padding: 1rem; flex-direction: column; align-items: flex-start;">
                        <span style="font-size: 2rem; font-weight: bold; color: var(--color-warning);">${metadata.total_charts || 0}</span>
                        <span>Charts Analyzed</span>
                    </div>
                    <div class="meta-badge" style="padding: 1rem; flex-direction: column; align-items: flex-start;">
                        <span style="font-size: 2rem; font-weight: bold; color: var(--color-info);">${countInterpretations()}</span>
                        <span>LLM Interpretations</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="series-card">
            <div class="series-header">
                <span class="series-name">Series Index</span>
            </div>
            <div class="series-content">
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                    ${(currentReport.series_index || []).map(s => `
                        <span class="meta-badge" style="cursor: pointer;" onclick="findSeriesPage('${s}')">${s}</span>
                    `).join('')}
                </div>
            </div>
        </div>

        <div class="series-card">
            <div class="series-header">
                <span class="series-name">Extraction Details</span>
            </div>
            <div class="series-content">
                <p><strong>Report ID:</strong> ${currentReport.report_id}</p>
                <p><strong>Extracted:</strong> ${metadata.extraction_date ? new Date(metadata.extraction_date).toLocaleString() : 'Unknown'}</p>
            </div>
        </div>
    `;
}

// Count LLM interpretations
function countInterpretations() {
    let count = 0;
    if (currentReport?.document_flow) {
        for (const page of currentReport.document_flow) {
            for (const block of page.blocks || []) {
                if (block.interpretation) count++;
            }
        }
    }
    return count;
}

// Update series tab
function updateSeries() {
    const content = document.getElementById('series-content');

    if (!currentReport?.document_flow) {
        content.innerHTML = '<div class="loading"><p>No series data available</p></div>';
        return;
    }

    const seriesPages = currentReport.document_flow.filter(page => page.series_name);

    if (seriesPages.length === 0) {
        content.innerHTML = '<div class="loading"><p>No series found in this report</p></div>';
        return;
    }

    content.innerHTML = seriesPages.map(page => {
        const textBlocks = page.blocks?.filter(b => b.block_type === 'text') || [];
        const textContent = textBlocks.map(b => b.content).join(' ').substring(0, 300);

        return `
            <div class="series-card fade-in">
                <div class="series-header">
                    <span class="series-name">${page.series_name}</span>
                    <span class="series-sector">${page.sector || 'Unknown'}</span>
                </div>
                <div class="series-content">
                    <p>${textContent}${textContent.length >= 300 ? '...' : ''}</p>
                    <div style="margin-top: 0.5rem;">
                        <span class="link-to-pdf" onclick="goToPage(${page.page_number})">
                            <i class="fas fa-external-link-alt"></i>
                            View in PDF (Page ${page.page_number})
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Update charts/LLM analysis tab
function updateCharts() {
    const content = document.getElementById('charts-content');

    if (!currentReport?.document_flow) {
        content.innerHTML = '<div class="loading"><p>No chart analysis available</p></div>';
        return;
    }

    const charts = [];
    for (const page of currentReport.document_flow) {
        for (const block of page.blocks || []) {
            if (block.block_type === 'chart' && block.interpretation) {
                charts.push({
                    page_number: page.page_number,
                    series_name: page.series_name,
                    ...block
                });
            }
        }
    }

    if (charts.length === 0) {
        content.innerHTML = '<div class="loading"><p>No chart interpretations available</p></div>';
        return;
    }

    content.innerHTML = charts.map(chart => {
        const interp = chart.interpretation || {};
        const phase = interp.current_phase || '?';
        const trend = interp.trend_direction || 'unknown';

        return `
            <div class="chart-card fade-in">
                <div class="chart-header">
                    <div>
                        <div class="chart-type">${chart.series_name || 'Unknown Series'}</div>
                        <div style="font-size: 0.75rem; color: var(--color-text-muted);">
                            ${chart.content?.chart_type || 'Chart'} - Page ${chart.page_number}
                        </div>
                    </div>
                    <div class="chart-phase phase-${phase}" title="Business Cycle Phase ${phase}">
                        ${phase}
                    </div>
                </div>

                <div class="chart-interpretation">
                    <p><strong>Analysis:</strong> ${interp.description || 'No description available'}</p>
                    ${interp.business_implications ? `
                        <p style="margin-top: 0.5rem;"><strong>Business Implications:</strong> ${interp.business_implications}</p>
                    ` : ''}
                </div>

                <div class="chart-meta">
                    <span class="meta-badge trend-${trend === 'rising' ? 'rising' : trend === 'falling' ? 'falling' : 'stable'}">
                        <i class="fas fa-${trend === 'rising' ? 'arrow-up' : trend === 'falling' ? 'arrow-down' : 'minus'}"></i>
                        ${trend}
                    </span>
                    ${interp.forecast_trend ? `
                        <span class="meta-badge">
                            <i class="fas fa-crystal-ball"></i>
                            Forecast: ${interp.forecast_trend}
                        </span>
                    ` : ''}
                    <span class="meta-badge">
                        <i class="fas fa-star"></i>
                        Confidence: ${interp.confidence || 'unknown'}
                    </span>
                    <span class="link-to-pdf" onclick="goToPage(${chart.page_number})">
                        <i class="fas fa-external-link-alt"></i>
                        View in PDF
                    </span>
                </div>

                ${interp.key_patterns?.length ? `
                    <div style="margin-top: 0.75rem;">
                        <strong style="font-size: 0.75rem;">Key Patterns:</strong>
                        <div style="display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.25rem;">
                            ${interp.key_patterns.map(p => `<span class="meta-badge">${p}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.data-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// Find series page
function findSeriesPage(seriesName) {
    if (!currentReport?.document_flow) return;

    const page = currentReport.document_flow.find(p => p.series_name === seriesName);
    if (page) {
        goToPage(page.page_number);
        switchTab('series');
    }
}

// Add AI context when report is selected
function addAIContext() {
    if (!currentReport) return;

    const contextMessage = `
I've loaded the report: **${currentReport.pdf_filename}**

- Report Period: ${currentReport.report_period || 'Unknown'}
- Total Pages: ${currentReport.metadata?.total_pages || 0}
- Series Extracted: ${currentReport.series_index?.length || 0}
- Charts Analyzed: ${currentReport.metadata?.total_charts || 0}
- LLM Interpretations: ${countInterpretations()}

How can I help you analyze this report?
    `.trim();

    addAIMessage('assistant', contextMessage);
}

// AI Chat functionality
function handleAIInput(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendAIMessage();
    }
}

async function sendAIMessage() {
    const input = document.getElementById('ai-input');
    const message = input.value.trim();

    if (!message) return;

    // Add user message
    addAIMessage('user', message);
    input.value = '';

    // Show loading
    const loadingId = addAIMessage('assistant', '<div class="spinner" style="width: 20px; height: 20px;"></div> Thinking...');

    try {
        const response = await fetch(`${API_BASE}/api/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                report_id: currentReport?.report_id,
                context: {
                    report: currentReport?.pdf_filename,
                    period: currentReport?.report_period,
                    series: currentReport?.series_index,
                    current_page: currentPage
                }
            })
        });

        if (!response.ok) throw new Error('AI request failed');

        const data = await response.json();

        // Remove loading message
        document.getElementById(loadingId)?.remove();

        // Add AI response
        addAIMessage('assistant', data.response);

        // If there are page references, highlight them
        if (data.page_references) {
            data.page_references.forEach(ref => {
                // Could add visual highlighting here
            });
        }

    } catch (error) {
        document.getElementById(loadingId)?.remove();
        addAIMessage('assistant', `Sorry, I encountered an error: ${error.message}. Please try again.`);
    }
}

function addAIMessage(role, content) {
    const messagesContainer = document.getElementById('ai-messages');
    const messageId = 'msg-' + Date.now();

    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `ai-message ${role} fade-in`;
    messageDiv.innerHTML = content;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageId;
}

function askQuickPrompt(prompt) {
    document.getElementById('ai-input').value = prompt;
    sendAIMessage();
}

// Upload functionality
function uploadPDF() {
    document.getElementById('upload-modal').style.display = 'flex';
}

function closeUploadModal() {
    document.getElementById('upload-modal').style.display = 'none';
}

async function submitUpload() {
    const fileInput = document.getElementById('pdf-file');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a PDF file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        addAIMessage('assistant', `Uploading and processing ${file.name}... This may take several minutes.`);
        closeUploadModal();

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        const data = await response.json();

        addAIMessage('assistant', `
            **Upload Complete!**

            - Report ID: ${data.report_id}
            - Pages: ${data.statistics?.total_pages || 0}
            - Series: ${data.statistics?.total_series || 0}
            - Charts: ${data.statistics?.total_charts || 0}
            - LLM Interpretations: ${data.statistics?.llm_interpretations || 0}
        `);

        // Refresh report list
        await loadReports();

        // Select the new report
        if (data.report_id) {
            selectReport(data.report_id);
        }

    } catch (error) {
        addAIMessage('assistant', `Upload failed: ${error.message}`);
    }
}

function refreshReports() {
    loadReports();
}

function showError(message) {
    addAIMessage('assistant', `<span style="color: var(--color-error);">${message}</span>`);
}

// Add modal styles dynamically
const modalStyles = document.createElement('style');
modalStyles.textContent = `
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    }
    .modal-content {
        background: var(--color-bg-secondary);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-xl);
        padding: var(--spacing-xl);
        min-width: 400px;
    }
    .modal-content h3 {
        margin-bottom: var(--spacing-lg);
    }
    .modal-content input[type="file"] {
        width: 100%;
        padding: var(--spacing-md);
        background: var(--color-bg-tertiary);
        border: 1px dashed var(--color-border);
        border-radius: var(--radius-md);
        color: var(--color-text-primary);
        margin-bottom: var(--spacing-lg);
    }
    .modal-actions {
        display: flex;
        gap: var(--spacing-sm);
        justify-content: flex-end;
    }
`;
document.head.appendChild(modalStyles);
