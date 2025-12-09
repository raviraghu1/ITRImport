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
            <div class="report-card fade-in" data-report-id="${report.report_id}" onclick="selectReport('${report.report_id}')">
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

    // Find and highlight the selected card using data attribute
    const selectedCard = document.querySelector(`.report-card[data-report-id="${reportId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('active');
    }

    try {
        console.log('Loading report:', reportId);
        const response = await fetch(`${API_BASE}/api/reports/${reportId}`);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error ${response.status}: ${errorText}`);
        }

        currentReport = await response.json();
        console.log('Report loaded:', currentReport.report_id);

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

        // Update analysis tab (NEW)
        updateAnalysisTab();

        // Update raw data tab
        document.getElementById('raw-content').textContent =
            JSON.stringify(currentReport, null, 2);

        // Add to AI context
        addAIContext();

        console.log('Report display complete');

    } catch (error) {
        console.error('Error loading report:', error);
        showError(`Failed to load report: ${error.message}`);
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

    // Update page indicator in data panel
    const pageIndicator = document.getElementById('current-page-indicator');
    if (pageIndicator) {
        pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
    }

    // Update the synced data panel to show current page content
    updateCurrentPageData();
}

// Update data panel to show content for current page
function updateCurrentPageData() {
    if (!currentReport?.document_flow) return;

    const pageData = currentReport.document_flow.find(p => p.page_number === currentPage);
    const content = document.getElementById('page-data-content');

    if (!content) return;

    if (!pageData) {
        content.innerHTML = `
            <div class="page-data-empty">
                <i class="fas fa-file-alt" style="font-size: 2rem; opacity: 0.3;"></i>
                <p>No extracted data for page ${currentPage}</p>
            </div>
        `;
        return;
    }

    // Get series info if available
    const seriesName = pageData.series_name;
    const seriesData = seriesName ? currentReport.series_index?.[seriesName] : null;
    const sector = pageData.sector || seriesData?.sector || '';
    const pageType = pageData.page_type || 'other';

    // Get all text content from all block types
    const allBlocks = pageData.blocks || [];
    const textBlocks = allBlocks.filter(b => b.block_type === 'text' || b.block_type === 'heading' || b.block_type === 'paragraph');
    let textContent = textBlocks.map(b => b.content).join('\n\n');

    // Also include page_summary if available
    if (pageData.page_summary && !textContent.includes(pageData.page_summary)) {
        textContent = pageData.page_summary + (textContent ? '\n\n' + textContent : '');
    }

    // Get chart interpretation
    let chartInterp = null;
    for (const block of allBlocks) {
        if (block.block_type === 'chart' && block.interpretation) {
            chartInterp = block.interpretation;
            break;
        }
    }

    // Page type badge mapping
    const pageTypeBadges = {
        'series': { label: 'Series', color: 'primary' },
        'table_of_contents': { label: 'Table of Contents', color: 'secondary' },
        'executive_summary': { label: 'Executive Summary', color: 'info' },
        'at_a_glance': { label: 'At-a-Glance', color: 'warning' },
        'other': { label: 'Overview', color: 'muted' }
    };

    const typeBadge = pageTypeBadges[pageType] || pageTypeBadges['other'];

    content.innerHTML = `
        <div class="page-data-card fade-in">
            <div class="page-data-header">
                ${seriesName ? `
                    <h4>${seriesName}</h4>
                    ${sector ? `<span class="series-sector">${sector}</span>` : ''}
                ` : `
                    <h4>Page ${currentPage}</h4>
                    <span class="page-type-badge badge-${typeBadge.color}">${typeBadge.label}</span>
                `}
            </div>

            ${seriesData?.summary ? `
                <div class="page-data-section">
                    <h5><i class="fas fa-file-alt"></i> Summary</h5>
                    <p class="summary-text">${seriesData.summary}</p>
                </div>
            ` : ''}

            ${chartInterp ? `
                <div class="page-data-section">
                    <h5><i class="fas fa-chart-line"></i> Chart Analysis</h5>
                    <div class="chart-analysis">
                        <div class="analysis-meta">
                            ${chartInterp.current_phase ? `
                                <span class="chart-phase phase-${chartInterp.current_phase}">Phase ${chartInterp.current_phase}</span>
                            ` : ''}
                            ${chartInterp.trend_direction ? `
                                <span class="meta-badge trend-${chartInterp.trend_direction === 'rising' ? 'rising' : chartInterp.trend_direction === 'falling' ? 'falling' : 'stable'}">
                                    <i class="fas fa-${chartInterp.trend_direction === 'rising' ? 'arrow-up' : chartInterp.trend_direction === 'falling' ? 'arrow-down' : 'minus'}"></i>
                                    ${chartInterp.trend_direction}
                                </span>
                            ` : ''}
                        </div>
                        <p>${chartInterp.description || ''}</p>
                        ${chartInterp.business_implications ? `
                            <p class="implications"><strong>Implications:</strong> ${chartInterp.business_implications}</p>
                        ` : ''}
                    </div>
                </div>
            ` : ''}

            ${textContent ? `
                <div class="page-data-section">
                    <h5><i class="fas fa-paragraph"></i> Extracted Text</h5>
                    <div class="extracted-text">${textContent}</div>
                </div>
            ` : `
                <div class="page-data-section">
                    <p style="color: var(--color-text-muted); font-style: italic;">No text content extracted for this page.</p>
                </div>
            `}

            ${renderCustomAnalyses(pageData.custom_analysis)}

            <div class="page-data-actions">
                <button class="btn btn-primary btn-sm" onclick="openAIAnalysisModal(${currentPage})">
                    <i class="fas fa-brain"></i>
                    Analyze with AI
                </button>
                <button class="business-insights-btn" onclick="openBusinessInsightsModal()">
                    <i class="fas fa-briefcase"></i>
                    Business Insights
                </button>
                ${seriesName ? `
                    <button class="btn btn-secondary btn-sm" onclick="openDocumentModal('${(seriesName || '').replace(/'/g, "\\'")}', ${currentPage})">
                        <i class="fas fa-expand"></i>
                        View Full Details
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

// Render saved custom analyses
function renderCustomAnalyses(customAnalysis) {
    if (!customAnalysis || (Array.isArray(customAnalysis) && customAnalysis.length === 0)) {
        return '';
    }

    const analyses = Array.isArray(customAnalysis) ? customAnalysis : [customAnalysis];

    return `
        <div class="page-data-section saved-analyses-section">
            <h5><i class="fas fa-brain"></i> Saved AI Analyses <span class="analysis-count">${analyses.length}</span></h5>
            <div class="saved-analyses-list">
                ${analyses.map((analysis, index) => `
                    <div class="saved-analysis-item">
                        <div class="saved-analysis-header">
                            <span class="analysis-type-badge">${formatAnalysisType(analysis.analysis_type)}</span>
                            <span class="analysis-timestamp">${formatTimestamp(analysis.timestamp)}</span>
                        </div>
                        ${analysis.analyst_context ? `
                            <div class="saved-analysis-context">
                                <i class="fas fa-comment"></i> ${analysis.analyst_context}
                            </div>
                        ` : ''}
                        <div class="saved-analysis-pages">
                            <i class="fas fa-file-alt"></i> Based on pages: ${analysis.pages_analyzed?.join(', ') || 'N/A'}
                        </div>
                        <div class="saved-analysis-content">${formatAnalysisPreview(analysis.content)}</div>
                        <button class="btn btn-sm btn-secondary" onclick="expandSavedAnalysis(${index})">
                            <i class="fas fa-expand"></i> View Full Analysis
                        </button>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Format analysis type for display
function formatAnalysisType(type) {
    const labels = {
        'general': 'General',
        'comparison': 'Comparison',
        'forecast': 'Forecast',
        'risks': 'Risks',
        'opportunities': 'Opportunities'
    };
    return labels[type] || type || 'Analysis';
}

// Format timestamp for display
function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Format analysis preview (first 300 chars)
function formatAnalysisPreview(content) {
    if (!content) return '';
    const preview = content.substring(0, 300);
    return preview + (content.length > 300 ? '...' : '');
}

// Expand saved analysis in a modal
// Store current viewed analysis for copy functionality
let currentViewedAnalysis = null;

function expandSavedAnalysis(index) {
    if (!currentReport?.document_flow) return;

    const pageData = currentReport.document_flow.find(p => p.page_number === currentPage);
    if (!pageData?.custom_analysis) return;

    const analyses = Array.isArray(pageData.custom_analysis) ? pageData.custom_analysis : [pageData.custom_analysis];
    const analysis = analyses[index];

    if (!analysis) return;

    // Store for copy functionality
    currentViewedAnalysis = analysis;

    // Update modal content
    const typeBadge = document.getElementById('view-analysis-type');
    typeBadge.textContent = formatAnalysisType(analysis.analysis_type);
    typeBadge.className = `view-analysis-type-badge ${analysis.analysis_type || 'general'}`;

    document.getElementById('view-analysis-timestamp').textContent = formatTimestamp(analysis.timestamp);

    // Update pages info
    const pagesEl = document.getElementById('view-analysis-pages');
    pagesEl.querySelector('span').textContent = `Based on pages: ${analysis.pages_analyzed?.join(', ') || 'N/A'}`;

    // Update context if exists
    const contextEl = document.getElementById('view-analysis-context');
    const contextTextEl = document.getElementById('view-analysis-context-text');
    if (analysis.analyst_context) {
        contextEl.style.display = 'flex';
        contextTextEl.textContent = analysis.analyst_context;
    } else {
        contextEl.style.display = 'none';
    }

    // Update content with formatted markdown
    const contentEl = document.getElementById('view-analysis-content');
    contentEl.innerHTML = formatMarkdown(analysis.content);

    // Show modal
    document.getElementById('view-analysis-modal').classList.add('active');
}

// Close view analysis modal
function closeViewAnalysisModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('view-analysis-modal').classList.remove('active');
}

// Copy viewed analysis to clipboard
function copyViewedAnalysis() {
    if (!currentViewedAnalysis) return;

    const text = `${formatAnalysisType(currentViewedAnalysis.analysis_type)} Analysis
Saved: ${formatTimestamp(currentViewedAnalysis.timestamp)}
Pages analyzed: ${currentViewedAnalysis.pages_analyzed?.join(', ') || 'N/A'}
${currentViewedAnalysis.analyst_context ? `Context: ${currentViewedAnalysis.analyst_context}\n` : ''}
---

${currentViewedAnalysis.content}`;

    navigator.clipboard.writeText(text).then(() => {
        // Show brief success feedback
        const btn = document.querySelector('.view-analysis-modal-footer .btn-secondary');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        btn.style.background = '#22c55e';
        btn.style.borderColor = '#22c55e';
        btn.style.color = 'white';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.background = '';
            btn.style.borderColor = '';
            btn.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Format markdown text to HTML
function formatMarkdown(text) {
    if (!text) return '';

    return text
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        // Wrap in paragraph
        .replace(/^/, '<p>')
        .replace(/$/, '</p>');
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

// Helper to get series names from series_index (handles both dict and array)
function getSeriesNames() {
    if (!currentReport?.series_index) return [];
    if (Array.isArray(currentReport.series_index)) {
        return currentReport.series_index;
    }
    // series_index is a dict with series names as keys
    return Object.keys(currentReport.series_index);
}

// Update overview tab
function updateOverview() {
    const content = document.getElementById('overview-content');

    if (!currentReport) {
        content.innerHTML = '<div class="loading"><p>Select a report to view details</p></div>';
        return;
    }

    const metadata = currentReport.metadata || {};
    const seriesNames = getSeriesNames();
    const seriesCount = seriesNames.length;

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
                    ${seriesNames.map(s => `
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
        const escapedSeriesName = (page.series_name || '').replace(/'/g, "\\'");

        return `
            <div class="series-card clickable fade-in" onclick="goToPageAndHighlight(${page.page_number}, '${escapedSeriesName}')">
                <div class="series-header">
                    <span class="series-name">${page.series_name}</span>
                    <span class="series-sector">${page.sector || 'Unknown'}</span>
                </div>
                <div class="series-content">
                    <p>${textContent}${textContent.length >= 300 ? '...' : ''}</p>
                    <a class="link-to-pdf" href="javascript:void(0)">
                        <i class="fas fa-external-link-alt"></i>
                        View in PDF (Page ${page.page_number})
                    </a>
                </div>
            </div>
        `;
    }).join('');
}

// Navigate to PDF page and highlight the series card
function goToPageAndHighlight(pageNum, seriesName) {
    // Navigate PDF to the page
    goToPage(pageNum);

    // Switch to Page Data tab to show synced view
    switchTab('pagedata');

    // Show message in AI panel
    addAIMessage('assistant', `Navigated to page ${pageNum}: ${seriesName}`);
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
        const escapedSeriesName = (chart.series_name || '').replace(/'/g, "\\'");

        return `
            <div class="chart-card clickable fade-in" onclick="openDocumentModal('${escapedSeriesName}', ${chart.page_number})">
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
                    <span class="link-to-pdf" onclick="event.stopPropagation(); goToPage(${chart.page_number})">
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
                <div class="view-full">
                    <i class="fas fa-expand"></i>
                    Click to view full document
                </div>
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

    const seriesNames = getSeriesNames();
    const contextMessage = `
I've loaded the report: **${currentReport.pdf_filename}**

- Report Period: ${currentReport.report_period || 'Unknown'}
- Total Pages: ${currentReport.metadata?.total_pages || 0}
- Series Extracted: ${seriesNames.length}
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
                    series: getSeriesNames(),
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

// Panel toggle functions
function toggleSidebar() {
    const container = document.getElementById('app-container');
    container.classList.toggle('sidebar-collapsed');
}

function toggleAIPanel() {
    const container = document.getElementById('app-container');
    container.classList.toggle('ai-collapsed');
}

// Document modal functions
function openDocumentModal(seriesName, pageNumber) {
    const modal = document.getElementById('document-modal');

    // Get series data from series_index
    const seriesData = currentReport?.series_index?.[seriesName];
    const pageData = currentReport?.document_flow?.find(p => p.page_number === pageNumber);

    // Set header info
    document.getElementById('modal-series-name').textContent = seriesName || 'Unknown Series';
    document.getElementById('modal-sector').textContent = seriesData?.sector || pageData?.sector || 'Unknown';

    // Set summary
    const summarySection = document.getElementById('modal-summary-section');
    const summaryEl = document.getElementById('modal-summary');
    if (seriesData?.summary) {
        summaryEl.textContent = seriesData.summary;
        summarySection.style.display = 'block';
    } else {
        summarySection.style.display = 'none';
    }

    // Set interpretation from chart blocks
    const interpSection = document.getElementById('modal-interpretation-section');
    const interpEl = document.getElementById('modal-interpretation');
    let interpretation = '';
    if (pageData?.blocks) {
        for (const block of pageData.blocks) {
            if (block.interpretation?.description) {
                interpretation = block.interpretation.description;
                if (block.interpretation.business_implications) {
                    interpretation += '\n\n**Business Implications:** ' + block.interpretation.business_implications;
                }
                break;
            }
        }
    }
    if (interpretation) {
        interpEl.innerHTML = interpretation.replace(/\n\n/g, '<br><br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        interpSection.style.display = 'block';
    } else {
        interpSection.style.display = 'none';
    }

    // Set insights
    const insightsSection = document.getElementById('modal-insights-section');
    const insightsEl = document.getElementById('modal-insights');
    const insights = seriesData?.insights || [];
    if (insights.length > 0) {
        insightsEl.innerHTML = insights.map(i => `<li>${i}</li>`).join('');
        insightsSection.style.display = 'block';
    } else {
        insightsSection.style.display = 'none';
    }

    // Set extracted text
    const textSection = document.getElementById('modal-text-section');
    const textEl = document.getElementById('modal-text');
    let extractedText = '';
    if (pageData?.blocks) {
        extractedText = pageData.blocks
            .filter(b => b.block_type === 'text' && b.content)
            .map(b => b.content)
            .join('\n\n');
    }
    if (extractedText) {
        textEl.textContent = extractedText;
        textSection.style.display = 'block';
    } else {
        textSection.style.display = 'none';
    }

    // Set page reference
    document.getElementById('modal-page-ref').textContent = `Page ${pageNumber}`;

    // Set goto button action
    const gotoBtn = document.getElementById('modal-goto-page');
    gotoBtn.onclick = () => {
        goToPage(pageNumber);
        closeDocumentModal();
    };

    // Show modal
    modal.classList.add('active');

    // Handle escape key
    document.addEventListener('keydown', handleModalEscape);
}

function closeDocumentModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('document-modal');
    modal.classList.remove('active');
    document.removeEventListener('keydown', handleModalEscape);
}

function handleModalEscape(event) {
    if (event.key === 'Escape') {
        closeDocumentModal();
    }
}

// ============================================================================
// Analysis Tab Functions (US1, US2, US3)
// ============================================================================

// Update the Analysis tab with overall and sector analysis
function updateAnalysisTab() {
    const content = document.getElementById('analysis-content');

    if (!currentReport) {
        content.innerHTML = '<div class="loading"><p>Select a report to view analysis</p></div>';
        return;
    }

    const overall = currentReport.overall_analysis;
    const sectors = currentReport.sector_analyses;
    const metadata = currentReport.analysis_metadata;

    if (!overall) {
        content.innerHTML = `
            <div class="analysis-empty">
                <i class="fas fa-brain" style="font-size: 3rem; opacity: 0.3; margin-bottom: 1rem;"></i>
                <p>No analysis available for this report.</p>
                <p style="font-size: 0.875rem; color: var(--color-text-muted); margin-bottom: 1rem;">
                    Generate LLM analysis from the extracted data.
                </p>
                <div class="generate-buttons">
                    <button id="generate-all-btn" class="btn btn-primary" onclick="generateAllSummaries()">
                        <i class="fas fa-magic"></i> Generate All Summaries
                    </button>
                    <button id="generate-overall-btn" class="btn btn-secondary" onclick="generateOverallSummary()">
                        <i class="fas fa-brain"></i> Generate Overall Only
                    </button>
                </div>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        ${renderGenerateActionsBar()}
        ${renderAnalysisMetadata(metadata)}
        ${renderSentimentScore(overall.sentiment_score)}
        ${renderExecutiveSummary(overall.executive_summary)}
        ${renderKeyThemes(overall.key_themes)}
        ${renderCrossSectorTrends(overall.cross_sector_trends)}
        ${renderRecommendations(overall.recommendations)}
        ${renderSectorNavigation(sectors)}
        <div id="sector-analysis-content"></div>
    `;
}

// Render action bar with generate/regenerate buttons
function renderGenerateActionsBar() {
    return `
        <div class="analysis-actions-bar">
            <div class="actions-left">
                <button id="generate-all-btn" class="btn btn-sm btn-primary" onclick="generateAllSummaries()" title="Regenerate all summaries">
                    <i class="fas fa-sync-alt"></i> Regenerate All
                </button>
                <button id="generate-overall-btn" class="btn btn-sm btn-secondary" onclick="generateOverallSummary(true)" title="Regenerate overall summary only">
                    <i class="fas fa-brain"></i> Regen Overall
                </button>
            </div>
            <div class="actions-right">
                <button class="btn btn-sm btn-secondary" onclick="exportAnalysis()" title="Export analysis to JSON">
                    <i class="fas fa-download"></i> Export
                </button>
            </div>
        </div>
    `;
}

// Render analysis metadata
function renderAnalysisMetadata(metadata) {
    if (!metadata) return '';

    const generatedAt = metadata.generated_at ? new Date(metadata.generated_at).toLocaleString() : 'Unknown';

    return `
        <div class="analysis-metadata">
            <span><i class="fas fa-clock"></i> Generated: ${generatedAt}</span>
            <span><i class="fas fa-robot"></i> Model: ${metadata.llm_model || 'Unknown'}</span>
            <span><i class="fas fa-stopwatch"></i> ${(metadata.processing_time_seconds || 0).toFixed(1)}s</span>
            ${metadata.regenerated_from_version ? `<span><i class="fas fa-redo"></i> Regenerated from v${metadata.regenerated_from_version}</span>` : ''}
        </div>
    `;
}

// Render sentiment score with visual indicator
function renderSentimentScore(sentiment) {
    if (!sentiment) return '';

    const scoreLabels = {
        1: { label: 'Strongly Bearish', class: 'bearish-strong', icon: 'fa-arrow-down' },
        2: { label: 'Bearish', class: 'bearish', icon: 'fa-arrow-down' },
        3: { label: 'Neutral', class: 'neutral', icon: 'fa-minus' },
        4: { label: 'Bullish', class: 'bullish', icon: 'fa-arrow-up' },
        5: { label: 'Strongly Bullish', class: 'bullish-strong', icon: 'fa-arrow-up' }
    };

    const scoreInfo = scoreLabels[sentiment.score] || scoreLabels[3];

    return `
        <div class="analysis-card sentiment-card ${scoreInfo.class}">
            <div class="sentiment-header">
                <div class="sentiment-score-display">
                    <div class="sentiment-gauge">
                        <div class="sentiment-value">${sentiment.score}</div>
                        <div class="sentiment-scale">
                            ${[1, 2, 3, 4, 5].map(n => `
                                <div class="scale-dot ${n === sentiment.score ? 'active' : ''} ${n <= 2 ? 'bearish' : n >= 4 ? 'bullish' : 'neutral'}"></div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="sentiment-label">
                        <i class="fas ${scoreInfo.icon}"></i>
                        ${sentiment.label || scoreInfo.label}
                    </div>
                </div>
                <div class="sentiment-confidence">
                    <span class="confidence-badge confidence-${sentiment.confidence || 'medium'}">
                        ${(sentiment.confidence || 'medium').toUpperCase()} Confidence
                    </span>
                </div>
            </div>

            <div class="sentiment-details">
                <p class="sentiment-rationale">${sentiment.rationale || ''}</p>

                ${sentiment.sector_weights ? `
                    <div class="sector-weights">
                        <h5>Sector Contributions</h5>
                        <div class="weights-bar">
                            ${Object.entries(sentiment.sector_weights).map(([sector, weight]) => `
                                <div class="weight-segment" style="width: ${weight * 100}%" title="${sector}: ${(weight * 100).toFixed(0)}%">
                                    <span class="weight-label">${sector}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                ${sentiment.contributing_factors?.length ? `
                    <div class="contributing-factors">
                        <h5>Contributing Factors</h5>
                        <div class="factors-list">
                            ${sentiment.contributing_factors.map(f => `
                                <div class="factor-item factor-${f.impact}">
                                    <span class="factor-name">${f.factor_name}</span>
                                    <span class="factor-impact ${f.impact}">${f.impact}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

// Render executive summary
function renderExecutiveSummary(summary) {
    if (!summary) return '';

    return `
        <div class="analysis-card">
            <div class="analysis-card-header">
                <h4><i class="fas fa-file-alt"></i> Executive Summary</h4>
            </div>
            <div class="analysis-card-content">
                <p class="executive-summary-text">${summary}</p>
            </div>
        </div>
    `;
}

// Render key themes
function renderKeyThemes(themes) {
    if (!themes || themes.length === 0) return '';

    return `
        <div class="analysis-card">
            <div class="analysis-card-header">
                <h4><i class="fas fa-lightbulb"></i> Key Themes</h4>
                <span class="theme-count">${themes.length} themes identified</span>
            </div>
            <div class="analysis-card-content">
                <div class="themes-grid">
                    ${themes.map(theme => `
                        <div class="theme-card" onclick="toggleThemeDetails(this)">
                            <div class="theme-header">
                                <span class="theme-name">${theme.theme_name}</span>
                                <span class="theme-score" title="Significance Score">
                                    <i class="fas fa-star"></i> ${theme.significance_score?.toFixed(1) || '?'}
                                </span>
                            </div>
                            <p class="theme-description">${theme.description || ''}</p>
                            <div class="theme-details" style="display: none;">
                                <div class="theme-meta">
                                    ${theme.affected_sectors?.length ? `
                                        <div class="theme-sectors">
                                            <strong>Affected Sectors:</strong>
                                            ${theme.affected_sectors.map(s => `<span class="sector-tag">${s}</span>`).join('')}
                                        </div>
                                    ` : ''}
                                    ${theme.source_pages?.length ? `
                                        <div class="theme-pages">
                                            <strong>Source Pages:</strong>
                                            ${theme.source_pages.map(p => `
                                                <span class="page-link" onclick="event.stopPropagation(); goToPage(${p})">p.${p}</span>
                                            `).join('')}
                                        </div>
                                    ` : ''}
                                </div>
                                ${theme.business_implications ? `
                                    <div class="theme-implications">
                                        <strong>Business Implications:</strong>
                                        <p>${theme.business_implications}</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

// Toggle theme details expansion
function toggleThemeDetails(element) {
    const details = element.querySelector('.theme-details');
    if (details) {
        details.style.display = details.style.display === 'none' ? 'block' : 'none';
        element.classList.toggle('expanded');
    }
}

// Render cross-sector trends
function renderCrossSectorTrends(trends) {
    if (!trends) return '';

    const directionIcons = {
        'expanding': { icon: 'fa-chart-line', class: 'positive' },
        'contracting': { icon: 'fa-chart-line-down', class: 'negative' },
        'mixed': { icon: 'fa-arrows-alt-h', class: 'neutral' },
        'transitioning': { icon: 'fa-exchange-alt', class: 'warning' }
    };

    const dirInfo = directionIcons[trends.overall_direction] || directionIcons['mixed'];

    return `
        <div class="analysis-card">
            <div class="analysis-card-header">
                <h4><i class="fas fa-project-diagram"></i> Cross-Sector Trends</h4>
                <span class="trend-direction ${dirInfo.class}">
                    <i class="fas ${dirInfo.icon}"></i>
                    ${trends.overall_direction?.toUpperCase() || 'MIXED'}
                </span>
            </div>
            <div class="analysis-card-content">
                <p class="trend-summary">${trends.trend_summary || ''}</p>

                <div class="sector-direction-grid">
                    ${trends.sectors_in_growth?.length ? `
                        <div class="sector-group growth">
                            <h5><i class="fas fa-arrow-up"></i> Sectors in Growth</h5>
                            <div class="sector-list">
                                ${trends.sectors_in_growth.map(s => `<span class="sector-badge growth">${s}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${trends.sectors_in_decline?.length ? `
                        <div class="sector-group decline">
                            <h5><i class="fas fa-arrow-down"></i> Sectors in Decline</h5>
                            <div class="sector-list">
                                ${trends.sectors_in_decline.map(s => `<span class="sector-badge decline">${s}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>

                ${trends.sector_correlations?.length ? `
                    <div class="correlations-section">
                        <h5>Sector Correlations</h5>
                        <div class="correlations-list">
                            ${trends.sector_correlations.slice(0, 3).map(c => `
                                <div class="correlation-item">
                                    <span class="correlation-sectors">${c.related_sector}</span>
                                    <span class="correlation-type">${c.relationship}</span>
                                    <span class="correlation-strength strength-${c.strength}">${c.strength}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

// Render recommendations
function renderRecommendations(recommendations) {
    if (!recommendations || recommendations.length === 0) return '';

    return `
        <div class="analysis-card">
            <div class="analysis-card-header">
                <h4><i class="fas fa-tasks"></i> Recommendations</h4>
            </div>
            <div class="analysis-card-content">
                <ul class="recommendations-list">
                    ${recommendations.map((rec, i) => `
                        <li class="recommendation-item">
                            <span class="rec-number">${i + 1}</span>
                            <span class="rec-text">${rec}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        </div>
    `;
}

// Render sector navigation
function renderSectorNavigation(sectors) {
    const allSectors = ['core', 'financial', 'construction', 'manufacturing'];
    const availableSectors = sectors ? Object.keys(sectors) : [];

    return `
        <div class="analysis-card">
            <div class="analysis-card-header">
                <h4><i class="fas fa-industry"></i> Sector Analysis</h4>
            </div>
            <div class="sector-nav">
                ${allSectors.map(sector => {
                    const hasData = availableSectors.includes(sector);
                    const sectorData = hasData ? sectors[sector] : null;
                    const hasSummary = sectorData && sectorData.summary;

                    return `
                        <div class="sector-nav-item">
                            <button class="sector-nav-btn ${hasData ? '' : 'no-data'}"
                                    onclick="showSectorAnalysis('${sector}')"
                                    ${!hasData ? 'disabled' : ''}>
                                <i class="fas fa-${getSectorIcon(sector)}"></i>
                                ${sector.charAt(0).toUpperCase() + sector.slice(1)}
                                ${!hasSummary ? '<span class="no-summary-badge">No Summary</span>' : ''}
                            </button>
                            <button class="generate-sector-btn btn btn-sm"
                                    data-sector="${sector}"
                                    onclick="event.stopPropagation(); generateSectorSummary('${sector}', true)"
                                    title="Generate/Regenerate ${sector} sector summary">
                                <i class="fas fa-magic"></i>
                            </button>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

// Get icon for sector
function getSectorIcon(sector) {
    const icons = {
        'core': 'chart-pie',
        'financial': 'dollar-sign',
        'construction': 'building',
        'manufacturing': 'industry'
    };
    return icons[sector] || 'chart-bar';
}

// Show sector analysis details
function showSectorAnalysis(sectorName) {
    const sectors = currentReport?.sector_analyses;
    if (!sectors || !sectors[sectorName]) return;

    const sector = sectors[sectorName];
    const container = document.getElementById('sector-analysis-content');

    // Highlight selected button
    document.querySelectorAll('.sector-nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase().includes(sectorName));
    });

    container.innerHTML = `
        <div class="sector-detail-card fade-in">
            <div class="sector-detail-header">
                <h4>
                    <i class="fas fa-${getSectorIcon(sectorName)}"></i>
                    ${sectorName.charAt(0).toUpperCase() + sectorName.slice(1)} Sector
                </h4>
                <span class="phase-badge phase-${sector.business_phase}">
                    Phase ${sector.business_phase}
                </span>
            </div>

            <div class="sector-summary">
                <p>${sector.summary || 'No summary available.'}</p>
            </div>

            <div class="sector-metrics">
                <div class="metric">
                    <span class="metric-value">${sector.series_count || 0}</span>
                    <span class="metric-label">Series</span>
                </div>
                <div class="metric">
                    <span class="metric-value trend-${sector.dominant_trend === 'accelerating' || sector.dominant_trend === 'recovering' ? 'rising' : sector.dominant_trend === 'declining' || sector.dominant_trend === 'slowing' ? 'falling' : 'stable'}">
                        ${sector.dominant_trend || 'stable'}
                    </span>
                    <span class="metric-label">Trend</span>
                </div>
            </div>

            ${sector.phase_distribution ? `
                <div class="phase-distribution">
                    <h5>Phase Distribution</h5>
                    <div class="phase-bars">
                        ${['A', 'B', 'C', 'D'].map(phase => {
                            const count = sector.phase_distribution[phase] || 0;
                            const total = Object.values(sector.phase_distribution).reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? (count / total * 100) : 0;
                            return `
                                <div class="phase-bar-container">
                                    <div class="phase-bar phase-${phase}" style="height: ${Math.max(pct, 5)}%"></div>
                                    <span class="phase-label">Phase ${phase}</span>
                                    <span class="phase-count">${count}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}

            ${sector.leading_indicators?.length ? `
                <div class="leading-indicators">
                    <h5>Leading Indicators</h5>
                    <ul>
                        ${sector.leading_indicators.map(ind => `<li>${ind}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${sector.key_insights?.length ? `
                <div class="key-insights">
                    <h5>Key Insights</h5>
                    <ul>
                        ${sector.key_insights.map(insight => `<li>${insight}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${sector.source_pages?.length ? `
                <div class="source-pages">
                    <h5>Source Pages</h5>
                    <div class="page-links">
                        ${sector.source_pages.map(p => `
                            <span class="page-link" onclick="goToPage(${p})">Page ${p}</span>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// Export analysis to PDF file
async function exportAnalysis(format = 'pdf') {
    if (!currentReport?.report_id) {
        alert('Please select a report first');
        return;
    }

    const btn = document.querySelector('.analysis-actions .btn-secondary[onclick*="exportAnalysis"]');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
    }

    addAIMessage('assistant', 'Generating PDF report... This may take a moment.');

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/analysis/export?format=${format}`);
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `ITR_Analysis_${currentReport.report_period || 'Report'}.pdf`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename=([^;]+)/);
            if (match) filename = match[1].replace(/"/g, '');
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        addAIMessage('assistant', 'PDF report exported successfully!');
    } catch (error) {
        addAIMessage('assistant', `Export failed: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-file-pdf"></i> Export PDF';
        }
    }
}

// ============================================================================
// On-Demand LLM Summary Generation Functions
// ============================================================================

// Generate overall summary using LLM
async function generateOverallSummary(forceRegenerate = false) {
    if (!currentReport?.report_id) {
        alert('Please select a report first');
        return;
    }

    const btn = document.getElementById('generate-overall-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    }

    addAIMessage('assistant', 'Generating overall summary... This may take a moment.');

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/generate-overall-summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force_regenerate: forceRegenerate })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }

        const result = await response.json();

        if (result.regenerated) {
            addAIMessage('assistant', `Overall summary ${forceRegenerate ? 'regenerated' : 'generated'} successfully! Processing time: ${result.processing_time?.toFixed(1) || '?'}s`);
        } else {
            addAIMessage('assistant', 'Overall summary already exists. Use "Regenerate" to create a new one.');
        }

        // Reload the report to show new analysis
        await selectReport(currentReport.report_id);
        switchTab('analysis');

    } catch (error) {
        addAIMessage('assistant', `Overall summary generation failed: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-brain"></i> Generate Overall Summary';
        }
    }
}

// Generate sector summary using LLM
async function generateSectorSummary(sector, forceRegenerate = false) {
    if (!currentReport?.report_id) {
        alert('Please select a report first');
        return;
    }

    const btn = document.querySelector(`.generate-sector-btn[data-sector="${sector}"]`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    addAIMessage('assistant', `Generating ${sector} sector summary...`);

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/generate-sector-summary/${sector}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force_regenerate: forceRegenerate })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }

        const result = await response.json();

        if (result.regenerated) {
            addAIMessage('assistant', `${sector.charAt(0).toUpperCase() + sector.slice(1)} sector summary generated!`);
        } else {
            addAIMessage('assistant', `${sector.charAt(0).toUpperCase() + sector.slice(1)} sector summary already exists.`);
        }

        // Reload the report to show new analysis
        await selectReport(currentReport.report_id);
        switchTab('analysis');
        // Show the sector that was just generated
        showSectorAnalysis(sector);

    } catch (error) {
        addAIMessage('assistant', `Sector summary generation failed: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i>';
        }
    }
}

// Generate all summaries (overall + all sectors)
async function generateAllSummaries() {
    if (!currentReport?.report_id) {
        alert('Please select a report first');
        return;
    }

    const btn = document.getElementById('generate-all-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating All...';
    }

    addAIMessage('assistant', 'Generating all summaries (overall + all sectors)... This may take a few minutes.');

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/generate-all-summaries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force_regenerate: true })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }

        const result = await response.json();

        addAIMessage('assistant', `All summaries generated successfully! Processing time: ${result.analysis_metadata?.processing_time_seconds?.toFixed(1) || '?'}s`);

        // Reload the report to show new analysis
        await selectReport(currentReport.report_id);
        switchTab('analysis');

    } catch (error) {
        addAIMessage('assistant', `Summary generation failed: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Generate All Summaries';
        }
    }
}

// Regenerate analysis
async function regenerateAnalysis() {
    if (!currentReport?.report_id) {
        alert('Please select a report first');
        return;
    }

    if (!confirm('This will regenerate the analysis using the current LLM. Continue?')) {
        return;
    }

    addAIMessage('assistant', 'Regenerating analysis... This may take a minute.');

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/regenerate-analysis`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Regeneration failed');

        const result = await response.json();

        addAIMessage('assistant', `Analysis regenerated successfully! Processing time: ${result.analysis_metadata?.processing_time_seconds?.toFixed(1) || '?'}s`);

        // Reload the report to show new analysis
        await selectReport(currentReport.report_id);

        // Switch to analysis tab
        switchTab('analysis');

    } catch (error) {
        addAIMessage('assistant', `Regeneration failed: ${error.message}`);
    }
}

// ============================================================================
// AI Analysis Modal Functions
// ============================================================================

let selectedPages = new Set();
let lastAnalysisResult = null;
let analysisTriggeredFromPage = null;  // Track which page triggered the analysis

// Open AI Analysis Modal
function openAIAnalysisModal(initialPage = null) {
    if (!currentReport) {
        alert('Please select a report first');
        return;
    }

    const modal = document.getElementById('ai-analysis-modal');
    modal.classList.add('active');

    // Reset state
    selectedPages.clear();
    lastAnalysisResult = null;
    analysisTriggeredFromPage = initialPage || currentPage;  // Track which page triggered this
    document.getElementById('analyst-context').value = '';
    document.getElementById('ai-analysis-results').style.display = 'none';
    document.querySelector('input[name="analysis-type"][value="general"]').checked = true;

    // Populate page grid
    populatePageGrid();

    // Pre-select initial page if provided
    if (initialPage) {
        togglePageSelection(initialPage);
    }

    updatePageSelectionUI();
}

// Close AI Analysis Modal
function closeAIAnalysisModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('ai-analysis-modal');
    modal.classList.remove('active');
}

// Populate page grid with checkboxes
function populatePageGrid() {
    const grid = document.getElementById('page-grid');
    const total = totalPages || 1;

    let html = '';
    for (let i = 1; i <= total; i++) {
        const pageData = currentReport?.document_flow?.find(p => p.page_number === i);
        const seriesName = pageData?.series_name || '';
        const pageType = pageData?.page_type || 'other';

        html += `
            <label class="page-checkbox ${selectedPages.has(i) ? 'selected' : ''}" data-page="${i}">
                <input type="checkbox" ${selectedPages.has(i) ? 'checked' : ''} onchange="togglePageSelection(${i})">
                <span class="page-number">${i}</span>
                <span class="page-label">${seriesName || pageType}</span>
            </label>
        `;
    }
    grid.innerHTML = html;
}

// Toggle page selection
function togglePageSelection(pageNum) {
    if (selectedPages.has(pageNum)) {
        selectedPages.delete(pageNum);
    } else {
        selectedPages.add(pageNum);
    }
    updatePageSelectionUI();
}

// Update page selection UI
function updatePageSelectionUI() {
    // Update checkboxes
    document.querySelectorAll('.page-checkbox').forEach(label => {
        const pageNum = parseInt(label.dataset.page);
        const checkbox = label.querySelector('input');
        if (selectedPages.has(pageNum)) {
            label.classList.add('selected');
            checkbox.checked = true;
        } else {
            label.classList.remove('selected');
            checkbox.checked = false;
        }
    });

    // Update selected pages display
    const display = document.getElementById('selected-pages-display');
    if (selectedPages.size === 0) {
        display.innerHTML = '<span class="placeholder">No pages selected</span>';
    } else {
        const sorted = Array.from(selectedPages).sort((a, b) => a - b);
        const rangeText = formatPageRanges(sorted);
        display.innerHTML = `<span class="selected-count">${selectedPages.size} page${selectedPages.size > 1 ? 's' : ''}</span>: ${rangeText}`;
    }

    // Update count and button state
    document.getElementById('pages-selected-count').textContent = `${selectedPages.size} page${selectedPages.size !== 1 ? 's' : ''} selected`;
    document.getElementById('run-analysis-btn').disabled = selectedPages.size === 0;
}

// Format page numbers as ranges
function formatPageRanges(pages) {
    if (pages.length === 0) return '';
    if (pages.length === 1) return `Page ${pages[0]}`;

    const ranges = [];
    let start = pages[0];
    let end = pages[0];

    for (let i = 1; i < pages.length; i++) {
        if (pages[i] === end + 1) {
            end = pages[i];
        } else {
            ranges.push(start === end ? `${start}` : `${start}-${end}`);
            start = pages[i];
            end = pages[i];
        }
    }
    ranges.push(start === end ? `${start}` : `${start}-${end}`);

    return ranges.join(', ');
}

// Select current page
function selectCurrentPage() {
    if (currentPage) {
        selectedPages.add(currentPage);
        updatePageSelectionUI();
    }
}

// Select all pages
function selectAllPages() {
    for (let i = 1; i <= totalPages; i++) {
        selectedPages.add(i);
    }
    updatePageSelectionUI();
}

// Select page range
function selectPageRange() {
    const rangeInput = prompt('Enter page range (e.g., "1-10" or "1,3,5-8"):', '');
    if (!rangeInput) return;

    const parts = rangeInput.split(',');
    for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed.includes('-')) {
            const [start, end] = trimmed.split('-').map(n => parseInt(n.trim()));
            if (!isNaN(start) && !isNaN(end)) {
                for (let i = Math.max(1, start); i <= Math.min(totalPages, end); i++) {
                    selectedPages.add(i);
                }
            }
        } else {
            const pageNum = parseInt(trimmed);
            if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
                selectedPages.add(pageNum);
            }
        }
    }
    updatePageSelectionUI();
}

// Clear page selection
function clearPageSelection() {
    selectedPages.clear();
    updatePageSelectionUI();
}

// Run AI Analysis
async function runAIAnalysis() {
    if (!currentReport?.report_id || selectedPages.size === 0) {
        alert('Please select at least one page to analyze');
        return;
    }

    const btn = document.getElementById('run-analysis-btn');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing... (may take up to 2 min)';
    btn.disabled = true;

    const analysisType = document.querySelector('input[name="analysis-type"]:checked').value;
    const analystContext = document.getElementById('analyst-context').value.trim();

    // Create AbortController for timeout (3 minutes)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000);

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/analyze-pages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pages: Array.from(selectedPages),
                analyst_context: analystContext,
                prompt_type: analysisType
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const result = await response.json();
        lastAnalysisResult = result;

        // Display results
        displayAnalysisResults(result);

        // Also add to AI chat
        addAIMessage('assistant', `**AI Analysis Complete** (${result.pages_analyzed.length} pages)\n\n${result.analysis.substring(0, 500)}...\n\n*View full results in the analysis modal*`);

    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            alert('Analysis timed out. Please try with fewer pages or try again later.');
        } else {
            alert(`Analysis failed: ${error.message}`);
        }
        console.error('Analysis error:', error);
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = selectedPages.size === 0;
    }
}

// Display analysis results
function displayAnalysisResults(result) {
    const resultsSection = document.getElementById('ai-analysis-results');
    const resultsContent = document.getElementById('analysis-results-content');

    // Format the analysis text with basic markdown
    let formattedAnalysis = result.analysis
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n- /g, '</p><li>')
        .replace(/\n(\d+)\. /g, '</p><li>')
        .replace(/^- /gm, '<li>')
        .replace(/^(\d+)\. /gm, '<li>');

    formattedAnalysis = '<p>' + formattedAnalysis + '</p>';

    // Build page details with series names
    const pageDetails = result.pages_analyzed.map(pageNum => {
        const pageData = currentReport?.document_flow?.find(p => p.page_number === pageNum);
        const seriesName = pageData?.series_name || '';
        const pageType = pageData?.page_type || '';
        const label = seriesName || pageType || 'Page ' + pageNum;
        return { pageNum, label };
    });

    // Format analysis type label
    const analysisTypeLabels = {
        'general': 'General Analysis',
        'comparison': 'Comparison Analysis',
        'forecast': 'Forecast Analysis',
        'risks': 'Risk Analysis',
        'opportunities': 'Opportunities Analysis'
    };

    resultsContent.innerHTML = `
        <div class="analysis-context-banner">
            <div class="context-banner-header">
                <i class="fas fa-info-circle"></i>
                <strong>Analysis Context</strong>
            </div>
            <div class="context-banner-details">
                <div class="context-item">
                    <span class="context-label">Analysis Type:</span>
                    <span class="context-value">${analysisTypeLabels[result.prompt_type] || result.prompt_type}</span>
                </div>
                <div class="context-item">
                    <span class="context-label">Pages Analyzed:</span>
                    <span class="context-value">${result.pages_analyzed.length} page${result.pages_analyzed.length > 1 ? 's' : ''}</span>
                </div>
                <div class="context-item">
                    <span class="context-label">Generated:</span>
                    <span class="context-value">${new Date(result.timestamp).toLocaleString()}</span>
                </div>
            </div>
            <div class="pages-analyzed-list">
                <span class="pages-label">Pages included in this analysis:</span>
                <div class="page-tags">
                    ${pageDetails.map(p => `
                        <span class="page-tag" onclick="goToPage(${p.pageNum})" title="Go to page ${p.pageNum}">
                            <span class="page-tag-number">${p.pageNum}</span>
                            <span class="page-tag-label">${p.label}</span>
                        </span>
                    `).join('')}
                </div>
            </div>
        </div>
        ${result.analyst_context ? `
            <div class="analyst-context-display">
                <i class="fas fa-user-edit"></i>
                <div>
                    <strong>Analyst Context Provided:</strong>
                    <p>${result.analyst_context}</p>
                </div>
            </div>
        ` : ''}
        <div class="analysis-text">
            ${formattedAnalysis}
        </div>
    `;

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Copy analysis results to clipboard
function copyAnalysisResults() {
    if (!lastAnalysisResult) return;

    const text = `AI Analysis - ${currentReport?.pdf_filename || 'Report'}
Pages Analyzed: ${lastAnalysisResult.pages_analyzed.join(', ')}
Analysis Type: ${lastAnalysisResult.prompt_type}
${lastAnalysisResult.analyst_context ? `Analyst Context: ${lastAnalysisResult.analyst_context}\n` : ''}
---

${lastAnalysisResult.analysis}
`;

    navigator.clipboard.writeText(text).then(() => {
        addAIMessage('assistant', 'Analysis copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Export analysis results
function exportAnalysisResults() {
    if (!lastAnalysisResult) return;

    const text = `AI Analysis Report
==================

Report: ${currentReport?.pdf_filename || 'Unknown'}
Date: ${new Date(lastAnalysisResult.timestamp).toLocaleString()}
Pages Analyzed: ${lastAnalysisResult.pages_analyzed.join(', ')}
Analysis Type: ${lastAnalysisResult.prompt_type}

${lastAnalysisResult.analyst_context ? `Analyst Context:
${lastAnalysisResult.analyst_context}

` : ''}Analysis Results:
----------------

${lastAnalysisResult.analysis}
`;

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-${currentReport?.report_id || 'report'}-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================================================
// Save Analysis Functions
// ============================================================================

// Open save analysis modal
async function saveAnalysisToPage() {
    if (!lastAnalysisResult || !currentReport?.report_id) {
        alert('No analysis to save');
        return;
    }

    const targetPage = analysisTriggeredFromPage || currentPage;
    document.getElementById('save-page-number').textContent = targetPage;

    // Check if page already has analysis
    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/page/${targetPage}/analysis`);
        const data = await response.json();

        const warningEl = document.getElementById('existing-analysis-warning');
        const modeOptionsEl = document.getElementById('save-mode-options');

        if (data.has_analysis) {
            warningEl.style.display = 'flex';
            modeOptionsEl.style.display = 'flex';
        } else {
            warningEl.style.display = 'none';
            modeOptionsEl.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking existing analysis:', error);
        document.getElementById('existing-analysis-warning').style.display = 'none';
        document.getElementById('save-mode-options').style.display = 'none';
    }

    // Show save modal
    document.getElementById('save-analysis-modal').classList.add('active');
}

// Close save analysis modal
function closeSaveAnalysisModal(event) {
    if (event && event.target !== event.currentTarget) return;
    resetSaveModal();
    document.getElementById('save-analysis-modal').classList.remove('active');
}

// Track the saved page for navigation
let lastSavedPage = null;

// Confirm and save the analysis
async function confirmSaveAnalysis() {
    if (!lastAnalysisResult || !currentReport?.report_id) {
        alert('No analysis to save');
        return;
    }

    const targetPage = analysisTriggeredFromPage || currentPage;
    const saveMode = document.querySelector('input[name="save-mode"]:checked')?.value || 'replace';

    const btn = document.getElementById('confirm-save-btn');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/save-page-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_number: targetPage,
                analysis: lastAnalysisResult.analysis,
                analysis_type: lastAnalysisResult.prompt_type,
                pages_analyzed: lastAnalysisResult.pages_analyzed,
                analyst_context: lastAnalysisResult.analyst_context || '',
                mode: saveMode
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }

        const result = await response.json();

        // Store the saved page for navigation
        lastSavedPage = targetPage;

        // Reload the report in the background to show the saved analysis
        await selectReport(currentReport.report_id);

        // Update success message
        const successText = document.getElementById('save-success-text');
        if (successText) {
            successText.textContent = `Analysis saved to Page ${targetPage}${result.total_analyses > 1 ? ` (${result.total_analyses} total)` : ''}`;
        }

        // Show success footer with navigation options
        document.getElementById('save-modal-actions').style.display = 'none';
        document.getElementById('save-success-actions').style.display = 'flex';

        // Hide the body content to focus on the success state
        document.querySelector('.save-analysis-modal-body').style.display = 'none';

        // Update header to show success
        const header = document.querySelector('.save-analysis-modal-header h3');
        if (header) {
            header.innerHTML = '<i class="fas fa-check-circle" style="color: var(--color-success);"></i> Analysis Saved';
        }

        // Show success message in AI panel
        addAIMessage('assistant', `✓ Analysis saved to page ${targetPage}. ${result.total_analyses > 1 ? `(${result.total_analyses} analyses on this page)` : ''}`);

    } catch (error) {
        alert(`Failed to save analysis: ${error.message}`);
        console.error('Save error:', error);
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

// Continue with AI Analysis - close save modal and return to analysis modal
function continueAIAnalysis() {
    // Reset save modal state
    resetSaveModal();

    // Close save modal
    document.getElementById('save-analysis-modal').classList.remove('active');

    // Clear the last analysis result to allow new analysis
    // but keep the page selection and context
    lastAnalysisResult = null;

    // Hide results and show inputs again in analysis modal
    document.getElementById('ai-analysis-results').style.display = 'none';

    // Focus on the analysis modal (should already be open)
    const analysisModal = document.getElementById('ai-analysis-modal');
    if (!analysisModal.classList.contains('active')) {
        analysisModal.classList.add('active');
    }
}

// Go to the saved page and close all modals
function goToSavedPage() {
    const pageToGo = lastSavedPage || analysisTriggeredFromPage || currentPage;

    // Reset save modal state
    resetSaveModal();

    // Close both modals
    document.getElementById('save-analysis-modal').classList.remove('active');
    document.getElementById('ai-analysis-modal').classList.remove('active');

    // Navigate to the page
    goToPage(pageToGo);
}

// Reset the save modal to its default state
function resetSaveModal() {
    // Show body content
    document.querySelector('.save-analysis-modal-body').style.display = 'block';

    // Reset header
    const header = document.querySelector('.save-analysis-modal-header h3');
    if (header) {
        header.innerHTML = '<i class="fas fa-save"></i> Save Analysis to Page';
    }

    // Show default footer, hide success footer
    document.getElementById('save-modal-actions').style.display = 'flex';
    document.getElementById('save-success-actions').style.display = 'none';

    // Reset save button
    const btn = document.getElementById('confirm-save-btn');
    btn.innerHTML = '<i class="fas fa-check"></i> Save Analysis';
    btn.disabled = false;
}

// ============================================================================
// Business Insights Functions
// ============================================================================

let currentBusinessInsights = null;

// Open business insights modal
function openBusinessInsightsModal() {
    if (!currentReport) {
        alert('Please select a report first');
        return;
    }

    // Update page info
    document.getElementById('insights-page-number').textContent = `Page ${currentPage}`;

    // Get series name if available
    const pageData = currentReport.document_flow?.find(p => p.page_number === currentPage);
    const seriesName = pageData?.series_name;
    const seriesInfo = document.getElementById('insights-series-info');

    if (seriesName) {
        document.getElementById('insights-series-name').textContent = seriesName;
        seriesInfo.style.display = 'flex';
    } else {
        seriesInfo.style.display = 'none';
    }

    // Reset modal state
    document.getElementById('business-context-input').value = '';
    document.getElementById('include-saved-analyses').checked = true;
    document.getElementById('business-insights-body').innerHTML = `
        <div class="insights-placeholder">
            <i class="fas fa-lightbulb"></i>
            <p>Click "Generate Insights" to extract actionable business modeling inputs from this page's content and analyses.</p>
        </div>
    `;
    document.getElementById('copy-insights-btn').style.display = 'none';
    document.getElementById('generate-insights-btn').disabled = false;
    document.getElementById('generate-insights-btn').innerHTML = '<i class="fas fa-magic"></i> Generate Insights';
    currentBusinessInsights = null;

    // Show modal
    document.getElementById('business-insights-modal').classList.add('active');
}

// Close business insights modal
function closeBusinessInsightsModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('business-insights-modal').classList.remove('active');
}

// Generate business insights
async function generateBusinessInsights() {
    if (!currentReport?.report_id) {
        alert('No report selected');
        return;
    }

    const businessContext = document.getElementById('business-context-input').value.trim();
    const includeSavedAnalyses = document.getElementById('include-saved-analyses').checked;

    const btn = document.getElementById('generate-insights-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

    // Show loading state
    document.getElementById('business-insights-body').innerHTML = `
        <div class="insights-loading">
            <div class="spinner"></div>
            <p>Generating business modeling insights...</p>
            <p style="font-size: 0.85em; opacity: 0.7;">This may take up to a minute</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/reports/${currentReport.report_id}/business-insights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_number: currentPage,
                include_saved_analyses: includeSavedAnalyses,
                business_context: businessContext
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate insights');
        }

        const result = await response.json();
        currentBusinessInsights = result.insights;

        // Display insights
        document.getElementById('business-insights-body').innerHTML = `
            <div class="insights-content">
                ${formatInsightsMarkdown(result.insights)}
            </div>
        `;

        // Show copy button
        document.getElementById('copy-insights-btn').style.display = 'inline-flex';

    } catch (error) {
        console.error('Business insights error:', error);
        document.getElementById('business-insights-body').innerHTML = `
            <div class="insights-placeholder" style="color: var(--color-danger);">
                <i class="fas fa-exclamation-circle"></i>
                <p>Failed to generate insights: ${error.message}</p>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> Generate Insights';
    }
}

// Format insights markdown to HTML
function formatInsightsMarkdown(text) {
    if (!text) return '';

    return text
        // Headers with emojis
        .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
        .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Bullet lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        // Numbered lists
        .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
        // Paragraphs
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        // Wrap
        .replace(/^/, '<p>')
        .replace(/$/, '</p>')
        // Clean up list items
        .replace(/<\/p><li>/g, '<ul><li>')
        .replace(/<\/li><p>/g, '</li></ul><p>')
        .replace(/<\/li><br><li>/g, '</li><li>');
}

// Copy business insights to clipboard
function copyBusinessInsights() {
    if (!currentBusinessInsights) return;

    navigator.clipboard.writeText(currentBusinessInsights).then(() => {
        const btn = document.getElementById('copy-insights-btn');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        btn.style.background = '#22c55e';
        btn.style.borderColor = '#22c55e';
        btn.style.color = 'white';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.background = '';
            btn.style.borderColor = '';
            btn.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Copy failed:', err);
        alert('Failed to copy to clipboard');
    });
}
