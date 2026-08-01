
// File: frontend/app.js

// Configuration - Update this after deployment
const API_BASE_URL = ''; // Will be set after SAM deployment, e.g., https://xxx.execute-api.region.amazonaws.com/prod

// State
let feeds = [];
let currentDigest = null;

// ============ Initialize ============
document.addEventListener('DOMContentLoaded', () => {
    loadFeeds();
    loadLatestDigest();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('addFeedBtn').addEventListener('click', addFeed);
    document.getElementById('refreshBtn').addEventListener('click', triggerDigestGeneration);
    document.getElementById('feedUrl').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addFeed();
    });
}

// ============ Feed Management ============
async function addFeed() {
    const urlInput = document.getElementById('feedUrl');
    const categorySelect = document.getElementById('feedCategory');
    const url = urlInput.value.trim();
    
    if (!url) {
        alert('Please enter a valid RSS feed URL');
        return;
    }
    
    const feed = {
        feed_id: generateId(),
        feed_url: url,
        category: categorySelect.value,
        status: 'active',
        added_at: new Date().toISOString()
    };
    
    try {
        if (API_BASE_URL) {
            await fetch(`${API_BASE_URL}/feeds`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(feed)
            });
        }
        
        feeds.push(feed);
        saveFeedsLocally();
        renderFeeds();
        urlInput.value = '';
    } catch (error) {
        console.error('Error adding feed:', error);
        // Still add locally for demo
        feeds.push(feed);
        saveFeedsLocally();
        renderFeeds();
    }
}

function removeFeed(feedId) {
    feeds = feeds.filter(f => f.feed_id !== feedId);
    saveFeedsLocally();
    renderFeeds();
}

function renderFeeds() {
    const container = document.getElementById('feedsList');
    if (feeds.length === 0) {
        container.innerHTML = '<p style="color: #718096; font-size: 14px;">No feeds configured yet. Add some above!</p>';
        return;
    }
    
    container.innerHTML = feeds.map(feed => `
        <div class="feed-chip">
            <span>${getCategoryEmoji(feed.category)} ${truncateUrl(feed.feed_url)}</span>
            <span class="remove" onclick="removeFeed('${feed.feed_id}')">✕</span>
        </div>
    `).join('');
}

// ============ Digest Display ============
async function loadLatestDigest() {
    try {
        if (API_BASE_URL) {
            const response = await fetch(`${API_BASE_URL}/digest/latest`);
            if (response.ok) {
                currentDigest = await response.json();
                renderDigest(currentDigest);
                return;
            }
        }
        
        // Load from localStorage for demo
        const saved = localStorage.getItem('smartdigest_demo');
        if (saved) {
            currentDigest = JSON.parse(saved);
            renderDigest(currentDigest);
        }
    } catch (error) {
        console.error('Error loading digest:', error);
    }
}

function renderDigest(digest) {
    const container = document.getElementById('digestContent');
    const articles = typeof digest.articles === 'string' ? JSON.parse(digest.articles) : digest.articles;
    
    if (!articles || articles.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No articles in this digest yet.</p></div>';
        return;
    }
    
    // Update stats
    document.getElementById('totalArticles').textContent = digest.total_articles || articles.length;
    document.getElementById('highCount').textContent = digest.high_priority || articles.filter(a => a.priority === 'high').length;
    document.getElementById('mediumCount').textContent = digest.medium_priority || articles.filter(a => a.priority === 'medium').length;
    document.getElementById('lowCount').textContent = digest.low_priority || articles.filter(a => a.priority === 'low').length;
    
    // Render articles grouped by priority
    let html = '';
    let currentPriority = null;
    const priorityLabels = { high: '🔴 Must Read', medium: '🟡 Worth Knowing', low: '🟢 Optional' };
    
    for (const article of articles) {
        if (article.priority !== currentPriority) {
            currentPriority = article.priority;
            html += `<h3 style="margin: 20px 0 12px; color: #4a5568;">${priorityLabels[currentPriority] || '⚪ Other'}</h3>`;
        }
        
        const tags = (article.tags || []).map(t => `<span class="tag">${t}</span>`).join('');
        
        html += `
            <div class="article-item priority-${article.priority || 'medium'}">
                <h3><a href="${article.link || '#'}" target="_blank">${article.title || 'Untitled'}</a></h3>
                <p class="summary">${article.summary || 'No summary available'}</p>
                <div class="tags">${tags}</div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// ============ Trigger Generation ============
async function triggerDigestGeneration() {
    const btn = document.getElementById('refreshBtn');
    btn.textContent = '⏳ Processing...';
    btn.disabled = true;
    
    try {
        if (API_BASE_URL) {
            await fetch(`${API_BASE_URL}/digest/generate`, { method: 'POST' });
            // Wait a moment then reload
            setTimeout(loadLatestDigest, 5000);
        } else {
            // Demo mode - generate sample digest
            generateDemoDigest();
        }
    } catch (error) {
        console.error('Error triggering generation:', error);
        generateDemoDigest();
    }
    
    setTimeout(() => {
        btn.textContent = '🔄 Generate Now';
        btn.disabled = false;
    }, 3000);
}

function generateDemoDigest() {
    const demoDigest = {
        digest_id: 'demo_' + Date.now(),
        total_articles: 8,
        high_priority: 2,
        medium_priority: 4,
        low_priority: 2,
        articles: [
            { title: 'AWS Announces New Bedrock Features for 2026', summary: 'Amazon Web Services expanded Bedrock with new Nova model capabilities including enhanced reasoning and multimodal support. Developers can now build more sophisticated AI applications with reduced latency.', priority: 'high', tags: ['AWS', 'AI', 'Bedrock'], link: '#', category: 'tech' },
            { title: 'Critical Security Update for Node.js Applications', summary: 'A high-severity vulnerability was discovered in popular npm packages. All Node.js developers should update their dependencies immediately to patch the exploit.', priority: 'high', tags: ['Security', 'Node.js'], link: '#', category: 'dev' },
            { title: 'The Rise of Serverless Architecture in 2026', summary: 'Serverless adoption continues to grow with 67% of enterprises now using Lambda or equivalent. Cost savings and developer productivity are the primary drivers.', priority: 'medium', tags: ['Serverless', 'Cloud'], link: '#', category: 'tech' },
            { title: 'Python 3.13 Performance Improvements', summary: 'The latest Python release brings significant performance gains with the new JIT compiler. Benchmarks show 2-3x speedup for compute-intensive workloads.', priority: 'medium', tags: ['Python', 'Performance'], link: '#', category: 'dev' },
            { title: 'DynamoDB Best Practices for Cost Optimization', summary: 'AWS published updated guidelines for DynamoDB cost management including on-demand vs provisioned capacity decisions and GSI optimization strategies.', priority: 'medium', tags: ['DynamoDB', 'AWS', 'Cost'], link: '#', category: 'tech' },
            { title: 'Remote Work Trends: Developer Productivity Report', summary: 'New research shows remote developers are 15% more productive but report higher burnout rates. Hybrid models with 2-3 office days show optimal balance.', priority: 'medium', tags: ['Remote Work', 'Productivity'], link: '#', category: 'business' },
            { title: 'Introduction to Rust for Systems Programming', summary: 'A comprehensive guide to getting started with Rust, covering ownership, borrowing, and common patterns for building reliable systems software.', priority: 'low', tags: ['Rust', 'Tutorial'], link: '#', category: 'dev' },
            { title: 'Weekly Roundup: Open Source Highlights', summary: 'This week featured notable releases including a new React framework, updates to Kubernetes, and an interesting ML library for edge computing.', priority: 'low', tags: ['Open Source', 'Roundup'], link: '#', category: 'dev' }
        ]
    };
    
    currentDigest = demoDigest;
    localStorage.setItem('smartdigest_demo', JSON.stringify(demoDigest));
    renderDigest(demoDigest);
}

// ============ Utilities ============
function loadFeeds() {
    const saved = localStorage.getItem('smartdigest_feeds');
    if (saved) {
        feeds = JSON.parse(saved);
    } else {
        // Default demo feeds
        feeds = [
            { feed_id: 'demo1', feed_url: 'https://aws.amazon.com/blogs/aws/feed/', category: 'tech', status: 'active' },
            { feed_id: 'demo2', feed_url: 'https://news.ycombinator.com/rss', category: 'tech', status: 'active' },
            { feed_id: 'demo3', feed_url: 'https://dev.to/feed', category: 'dev', status: 'active' }
        ];
    }
    renderFeeds();
}

function saveFeedsLocally() {
    localStorage.setItem('smartdigest_feeds', JSON.stringify(feeds));
}

function generateId() {
    return Math.random().toString(36).substring(2, 10);
}

function truncateUrl(url) {
    try {
        const hostname = new URL(url).hostname;
        return hostname.replace('www.', '');
    } catch {
        return url.substring(0, 30) + '...';
    }
}

function getCategoryEmoji(category) {
    const emojis = {
        tech: '💻', business: '📊', science: '🔬',
        ai: '🤖', news: '📰', dev: '⚡'
    };
    return emojis[category] || '📄';
}