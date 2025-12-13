/*
Aurora OS Enterprise Console - JavaScript
Real-time updates, interactivity, and API communication
*/

// Global state
let authToken = localStorage.getItem('aurora_token');
let currentUser = null;
let websocket = null;
let refreshIntervals = {};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    try {
        // Check authentication
        if (!authToken) {
            window.location.href = '/login.html';
            return;
        }
        
        // Initialize WebSocket connection
        initializeWebSocket();
        
        // Load user data
        await loadUserData();
        
        // Setup navigation
        setupNavigation();
        
        // Setup real-time updates
        setupRealTimeUpdates();
        
        // Load initial data
        loadDashboardData();
        
        console.log('Aurora Enterprise Console initialized');
        
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('Failed to initialize application');
    }
}

// WebSocket Management
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(event) {
        console.log('WebSocket connected');
        showSuccess('Real-time updates connected');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(initializeWebSocket, 5000);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
        showWarning('Real-time updates unavailable');
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'node_registered':
            handleNodeRegistered(data.node);
            break;
        case 'node_updated':
            handleNodeUpdated(data.node);
            break;
        case 'policy_deployed':
            handlePolicyDeployed(data.policy);
            break;
        case 'compliance_update':
            handleComplianceUpdate(data.compliance);
            break;
        case 'system_alert':
            handleSystemAlert(data.alert);
            break;
        default:
            console.log('Unknown WebSocket message type:', data.type);
    }
}

// Authentication
async function login(username, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('aurora_token', authToken);
            window.location.href = '/';
        } else {
            const error = await response.json();
            showError(error.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Login failed. Please try again.');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('aurora_token');
    
    // Call logout API
    fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    }).catch(console.error);
    
    window.location.href = '/login.html';
}

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(endpoint, finalOptions);
        
        if (response.status === 401) {
            // Token expired, redirect to login
            logout();
            return;
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API call failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}

// Data Loading Functions
async function loadUserData() {
    try {
        // Decode JWT to get user info (in production, validate on backend)
        const tokenPayload = JSON.parse(atob(authToken.split('.')[1]));
        currentUser = {
            id: tokenPayload.user_id,
            username: tokenPayload.username,
            role: tokenPayload.role
        };
        
        updateUIForUserRole();
    } catch (error) {
        console.error('Failed to load user data:', error);
        logout();
    }
}

async function loadDashboardData() {
    try {
        const [nodesData, policiesData, modesData] = await Promise.all([
            apiCall('/api/nodes'),
            apiCall('/api/policies'),
            apiCall('/api/modes')
        ]);
        
        updateDashboardStats(nodesData, policiesData, modesData);
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        showError('Failed to load dashboard data');
    }
}

async function loadNodes() {
    try {
        const data = await apiCall('/api/nodes');
        updateNodesTable(data.nodes);
    } catch (error) {
        console.error('Failed to load nodes:', error);
        showError('Failed to load nodes');
    }
}

async function loadPolicies() {
    try {
        const data = await apiCall('/api/policies');
        updatePoliciesList(data.policies);
    } catch (error) {
        console.error('Failed to load policies:', error);
        showError('Failed to load policies');
    }
}

async function loadComplianceData() {
    try {
        const data = await apiCall('/api/compliance');
        updateComplianceTable(data.compliance);
        updateComplianceScore(data.overall_compliance);
    } catch (error) {
        console.error('Failed to load compliance data:', error);
        showError('Failed to load compliance data');
    }
}

// UI Update Functions
function updateDashboardStats(nodesData, policiesData, modesData) {
    // Update node counts
    document.getElementById('total-nodes').textContent = nodesData.total;
    document.getElementById('online-nodes').textContent = nodesData.online;
    document.getElementById('offline-nodes').textContent = nodesData.total - nodesData.online;
    
    // Update policy counts
    document.getElementById('active-policies').textContent = policiesData.active;
    
    // Update Aurora mode counts
    const modeCounts = modesData.current_mode_distribution;
    document.getElementById('enterprise-nodes').textContent = modeCounts.enterprise || 0;
    document.getElementById('developer-nodes').textContent = modeCounts.developer || 0;
    document.getElementById('personal-nodes').textContent = modeCounts.personal || 0;
}

function updateNodesTable(nodes) {
    const tbody = document.getElementById('nodes-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    nodes.forEach(node => {
        const row = createNodeRow(node);
        tbody.appendChild(row);
    });
}

function createNodeRow(node) {
    const row = document.createElement('tr');
    
    const statusClass = node.status === 'online' ? 'status-online' : 'status-offline';
    const modeClass = `mode-${node.aurora_mode}`;
    
    row.innerHTML = `
        <td>
            <strong>${node.name}</strong>
            <br><small>${node.hostname}</small>
        </td>
        <td>
            <span class="status-badge ${statusClass}">
                <span class="status-indicator ${statusClass}"></span>
                ${node.status}
            </span>
        </td>
        <td>
            <span class="mode-badge ${modeClass}">${node.aurora_mode}</span>
        </td>
        <td>${node.ip_address}</td>
        <td>${node.location}</td>
        <td>${node.department}</td>
        <td>${formatDate(node.last_seen)}</td>
        <td>
            <button class="btn btn-primary btn-sm" onclick="configureNode('${node.id}')">
                Configure
            </button>
            <button class="btn btn-secondary btn-sm" onclick="viewNodeDetails('${node.id}')">
                Details
            </button>
        </td>
    `;
    
    return row;
}

function updatePoliciesList(policies) {
    const container = document.getElementById('policies-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    policies.forEach(policy => {
        const policyCard = createPolicyCard(policy);
        container.appendChild(policyCard);
    });
}

function createPolicyCard(policy) {
    const card = document.createElement('div');
    card.className = 'policy-card fade-in';
    
    const statusClass = policy.active ? 'status-active' : 'status-inactive';
    const statusText = policy.active ? 'Active' : 'Inactive';
    
    card.innerHTML = `
        <div class="policy-header">
            <div class="policy-name">${policy.name}</div>
            <div>
                <span class="policy-status ${statusClass}">${statusText}</span>
                <button class="btn btn-primary btn-sm" onclick="editPolicy('${policy.id}')">
                    Edit
                </button>
                <button class="btn btn-secondary btn-sm" onclick="deployPolicy('${policy.id}')">
                    Deploy
                </button>
            </div>
        </div>
        <p>${policy.description}</p>
        <p><strong>Compliance Level:</strong> ${policy.compliance_level}</p>
        <p><strong>Target Nodes:</strong> ${policy.target_nodes.length} nodes</p>
        <p><strong>Created:</strong> ${formatDate(policy.created_at)}</p>
    `;
    
    return card;
}

function updateComplianceTable(compliance) {
    const tbody = document.getElementById('compliance-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    compliance.forEach(node => {
        const row = createComplianceRow(node);
        tbody.appendChild(row);
    });
}

function createComplianceRow(node) {
    const row = document.createElement('tr');
    
    let statusClass = 'compliance-good';
    let statusText = 'Compliant';
    
    if (node.score < 80) {
        statusClass = 'compliance-error';
        statusText = 'Non-Compliant';
    } else if (node.score < 95) {
        statusClass = 'compliance-warning';
        statusText = 'Warning';
    }
    
    row.innerHTML = `
        <td><strong>${node.node_name}</strong></td>
        <td>${node.compliance_level.toUpperCase()}</td>
        <td class="${statusClass}">${statusText}</td>
        <td>${formatDate(node.last_check)}</td>
        <td>${node.score}%</td>
        <td>
            <button class="btn btn-primary btn-sm" onclick="viewComplianceDetails('${node.node_id}')">
                Details
            </button>
        </td>
    `;
    
    return row;
}

function updateComplianceScore(score) {
    const scoreElement = document.getElementById('compliance-score-value');
    if (!scoreElement) return;
    
    scoreElement.textContent = `${score}%`;
    
    // Update color based on score
    scoreElement.className = 'score-value';
    if (score < 80) {
        scoreElement.classList.add('error');
    } else if (score < 95) {
        scoreElement.classList.add('warning');
    }
}

// Real-time Event Handlers
function handleNodeRegistered(node) {
    showSuccess(`Node "${node.name}" registered successfully`);
    
    // Refresh data if on relevant page
    if (window.location.pathname === '/' || window.location.pathname === '/nodes') {
        loadDashboardData();
        loadNodes();
    }
}

function handleNodeUpdated(node) {
    showInfo(`Node "${node.name}" updated`);
    
    // Update node in table if on nodes page
    const row = document.querySelector(`tr[data-node-id="${node.id}"]`);
    if (row) {
        const newRow = createNodeRow(node);
        newRow.setAttribute('data-node-id', node.id);
        row.replaceWith(newRow);
    }
}

function handlePolicyDeployed(policy) {
    showSuccess(`Policy "${policy.name}" deployed successfully`);
    
    // Refresh policies if on relevant page
    if (window.location.pathname === '/' || window.location.pathname === '/policies') {
        loadPolicies();
    }
}

function handleComplianceUpdate(compliance) {
    showInfo('Compliance status updated');
    
    // Refresh compliance if on relevant page
    if (window.location.pathname === '/compliance') {
        loadComplianceData();
    }
}

function handleSystemAlert(alert) {
    if (alert.severity === 'error') {
        showError(alert.message);
    } else if (alert.severity === 'warning') {
        showWarning(alert.message);
    } else {
        showInfo(alert.message);
    }
}

// Action Functions
function configureNode(nodeId) {
    // Open configuration modal
    openModal('configure-node-modal');
    
    // Load node data into form
    // Implementation depends on specific requirements
    console.log('Configure node:', nodeId);
}

function viewNodeDetails(nodeId) {
    // Navigate to node details page or open modal
    window.location.href = `/nodes/${nodeId}`;
}

function editPolicy(policyId) {
    // Open policy edit modal
    openModal('edit-policy-modal');
    
    // Load policy data into form
    console.log('Edit policy:', policyId);
}

function deployPolicy(policyId) {
    if (confirm('Are you sure you want to deploy this policy?')) {
        deployPolicyToNodes(policyId);
    }
}

async function deployPolicyToNodes(policyId) {
    try {
        showLoading('Deploying policy...');
        
        await apiCall(`/api/policies/${policyId}/deploy`, {
            method: 'POST'
        });
        
        hideLoading();
        showSuccess('Policy deployed successfully');
    } catch (error) {
        hideLoading();
        showError('Failed to deploy policy: ' + error.message);
    }
}

function createPolicy() {
    openModal('create-policy-modal');
}

function viewComplianceDetails(nodeId) {
    // Open compliance details modal
    openModal('compliance-details-modal');
    console.log('View compliance details for:', nodeId);
}

// Navigation
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-menu a');
    const currentPath = window.location.pathname;
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
        
        link.addEventListener('click', function(e) {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function navigateToPage(page) {
    window.location.href = page;
}

// Real-time Updates
function setupRealTimeUpdates() {
    // Set up periodic data refresh
    setupAutoRefresh();
}

function setupAutoRefresh() {
    // Clear existing intervals
    Object.values(refreshIntervals).forEach(clearInterval);
    
    // Set refresh intervals based on current page
    const currentPath = window.location.pathname;
    
    if (currentPath === '/' || currentPath === '/nodes') {
        refreshIntervals.nodes = setInterval(loadNodes, 30000);
    }
    
    if (currentPath === '/' || currentPath === '/policies') {
        refreshIntervals.policies = setInterval(loadPolicies, 60000);
    }
    
    if (currentPath === '/compliance') {
        refreshIntervals.compliance = setInterval(loadComplianceData, 60000);
    }
    
    if (currentPath === '/monitoring') {
        refreshIntervals.monitoring = setInterval(updateMetrics, 5000);
    }
}

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateUIForUserRole() {
    // Hide/show elements based on user role
    if (currentUser) {
        const adminElements = document.querySelectorAll('.admin-only');
        const operatorElements = document.querySelectorAll('.operator-only');
        const viewerElements = document.querySelectorAll('.viewer-only');
        
        if (currentUser.role === 'viewer') {
            adminElements.forEach(el => el.style.display = 'none');
            operatorElements.forEach(el => el.style.display = 'none');
        } else if (currentUser.role === 'operator') {
            adminElements.forEach(el => el.style.display = 'none');
        }
    }
}

// Modal Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Loading and Notification Functions
function showLoading(message = 'Loading...') {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-overlay';
    loadingDiv.className = 'loading-overlay';
    loadingDiv.innerHTML = `
        <div class="loading-content">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
    document.body.appendChild(loadingDiv);
}

function hideLoading() {
    const loadingDiv = document.getElementById('loading-overlay');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showWarning(message) {
    showNotification(message, 'warning');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Add to top of page
    document.body.insertBefore(notification, document.body.firstChild);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Monitoring metrics update
function updateMetrics() {
    // Simulate metric updates (in production, this would come from API)
    const metrics = {
        cpuUsage: Math.floor(Math.random() * 40 + 10),
        memoryUsage: Math.floor(Math.random() * 30 + 50),
        responseTime: Math.floor(Math.random() * 50 + 50),
        networkIO: Math.floor(Math.random() * 100 + 20)
    };
    
    // Update metric displays
    const cpuElement = document.getElementById('cpu-usage');
    const memoryElement = document.getElementById('memory-usage');
    const responseElement = document.getElementById('response-time');
    
    if (cpuElement) cpuElement.textContent = `${metrics.cpuUsage}%`;
    if (memoryElement) memoryElement.textContent = `${metrics.memoryUsage}%`;
    if (responseElement) responseElement.textContent = `${metrics.responseTime}ms`;
}

// Export functions for global access
window.AuroraEnterprise = {
    login,
    logout,
    configureNode,
    viewNodeDetails,
    editPolicy,
    deployPolicy,
    createPolicy,
    viewComplianceDetails,
    navigateToPage,
    openModal,
    closeModal,
    showNotification
};