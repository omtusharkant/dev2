// Main JavaScript functionality for the Workflow Manager

let currentSection = 'welcome-section';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeFeatherIcons();
});

// Navigation functionality
function initializeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const section = this.getAttribute('data-section');
            if (section) {
                showSection(section);
                setActiveNavItem(this);
            }
        });
    });
}

function showSection(sectionId) {
    // Hide all sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
        currentSection = sectionId;
    }
    
    // Hide results section when switching
    hideResults();
    
    // Re-initialize Feather icons
    setTimeout(() => {
        feather.replace();
    }, 100);
}

function setActiveNavItem(activeItem) {
    // Remove active class from all nav items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to clicked item
    activeItem.classList.add('active');
}

function initializeFeatherIcons() {
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// API Request functionality
async function tryRequest(method, endpoint) {
    showLoading();
    
    try {
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        showResults(response.status, data);
        
    } catch (error) {
        showResults(500, { error: error.message });
    }
}

async function tryRequestWithBody(method, endpoint, bodyElementId) {
    const bodyElement = document.getElementById(bodyElementId);
    if (!bodyElement) {
        showResults(400, { error: 'Request body element not found' });
        return;
    }
    
    let requestBody;
    try {
        requestBody = JSON.parse(bodyElement.value);
    } catch (error) {
        showResults(400, { error: 'Invalid JSON in request body' });
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        showResults(response.status, data);
        
    } catch (error) {
        showResults(500, { error: error.message });
    }
}

async function executeNode() {
    const nodeIdElement = document.getElementById('execute-node-id');
    const bodyElement = document.getElementById('execute-node-body');
    
    if (!nodeIdElement.value) {
        showResults(400, { error: 'Node ID is required' });
        return;
    }
    
    const nodeId = parseInt(nodeIdElement.value);
    const endpoint = `/api/nodes/${nodeId}/execute`;
    
    let requestBody;
    try {
        requestBody = JSON.parse(bodyElement.value);
    } catch (error) {
        showResults(400, { error: 'Invalid JSON in request body' });
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        showResults(response.status, data);
        
    } catch (error) {
        showResults(500, { error: error.message });
    }
}

async function loadNodeTypes() {
    showLoading();
    
    try {
        const response = await fetch('/api/node-types', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        displayNodeTypes(data);
        
    } catch (error) {
        showResults(500, { error: error.message });
    }
}

function displayNodeTypes(nodeTypes) {
    const resultContainer = document.getElementById('node-types-result');
    
    let html = '<div class="node-types-container">';
    
    Object.entries(nodeTypes).forEach(([type, info]) => {
        html += `
            <div class="node-type-card">
                <div class="node-type-header">
                    <span class="node-type-badge">${type}</span>
                    <h6 class="mb-0">${info.name}</h6>
                </div>
                <p class="text-muted mb-3">${info.description}</p>
                
                <h6>Parameters:</h6>
                <div class="parameter-list">
        `;
        
        Object.entries(info.parameters).forEach(([paramName, paramInfo]) => {
            html += `
                <div class="parameter-item">
                    <div class="d-flex align-items-center">
                        <span class="parameter-name">${paramName}</span>
                        <span class="parameter-type">${paramInfo.type}</span>
                        ${paramInfo.required ? '<span class="parameter-required">required</span>' : ''}
                    </div>
                    <div class="parameter-description">${paramInfo.description}</div>
                    ${paramInfo.default !== undefined ? `<div class="text-muted small">Default: ${paramInfo.default}</div>` : ''}
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    resultContainer.innerHTML = html;
    showResults(200, null, false);
}

function showLoading() {
    const resultsSection = document.getElementById('results-section');
    const responseStatus = document.getElementById('response-status');
    const responseBody = document.getElementById('response-body');
    
    responseStatus.innerHTML = '<span class="text-muted">Loading...</span>';
    responseBody.textContent = '';
    resultsSection.style.display = 'block';
}

function showResults(status, data, showJson = true) {
    const resultsSection = document.getElementById('results-section');
    const responseStatus = document.getElementById('response-status');
    const responseBody = document.getElementById('response-body');
    
    // Show status
    const statusClass = status >= 200 && status < 300 ? 'status-success' : 'status-error';
    responseStatus.innerHTML = `<span class="${statusClass}">Status: ${status}</span>`;
    
    // Show response body if JSON should be displayed
    if (showJson && data) {
        responseBody.textContent = JSON.stringify(data, null, 2);
    } else if (!showJson) {
        responseBody.textContent = '';
    }
    
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideResults() {
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'none';
}

// Utility functions
function formatJSON(obj) {
    return JSON.stringify(obj, null, 2);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Could add a toast notification here
        console.log('Copied to clipboard');
    });
}

// Export functions for global access
window.showSection = showSection;
window.tryRequest = tryRequest;
window.tryRequestWithBody = tryRequestWithBody;
window.executeNode = executeNode;
window.loadNodeTypes = loadNodeTypes;
