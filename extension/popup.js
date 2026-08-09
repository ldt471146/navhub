// NavHub popup: 一键收藏当前标签页，AI 自动分类
const SERVER_KEY = 'navhub_server';
const DEFAULT_SERVER = 'https://nav.example.com';

const statusEl = document.getElementById('status');
const suggestEl = document.getElementById('suggest');
const saveBtn = document.getElementById('saveBtn');

function setStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = 'status ' + (type || '');
}

function getServer() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([SERVER_KEY], (r) => resolve(r[SERVER_KEY] || DEFAULT_SERVER));
  });
}

async function api(server, path, body) {
  const resp = await fetch(server + path, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (resp.status === 401) throw new Error('NOT_LOGGED_IN');
  if (!resp.ok) {
    let detail = resp.statusText;
    try { detail = (await resp.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return resp.json();
}

saveBtn.addEventListener('click', async () => {
  const server = await getServer();
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || !/^https?:/.test(tab.url)) {
    setStatus('当前页面不支持收藏（如浏览器内部页）', 'err');
    return;
  }

  saveBtn.disabled = true;
  setStatus('AI 分析中…', 'loading');
  suggestEl.className = 'suggest';

  try {
    // 1. AI 分类建议
    const classify = await api(server, '/api/sites/ai-classify', { url: tab.url });
    const page = classify.page;
    const sug = classify.suggestion;

    // 2. 决定保存目标分类
    let categoryId = null;
    let newCategory = null;
    if (sug.category) {
      const cats = await (await fetch(server + '/api/categories', { credentials: 'include' })).json();
      const hit = cats.find(c => c.name === sug.category);
      if (hit) categoryId = hit.id;
      else newCategory = sug.category;
    } else if (sug.new_category) {
      newCategory = sug.new_category;
    }

    // 3. 保存
    await api(server, '/api/sites/ai-save', {
      url: page.url,
      title: tab.title || page.title,
      description: page.description,
      favicon: page.favicon,
      category_id: categoryId,
      new_category: newCategory,
    });

    const target = newCategory || sug.category || '未分类';
    setStatus('✅ 已收藏到「' + target + '」', 'ok');
    suggestEl.textContent = 'AI 判断：' + (sug.reason || '') + '（置信度 ' + Math.round((sug.confidence || 0) * 100) + '%）';
    suggestEl.className = 'suggest show';
  } catch (e) {
    if (e.message === 'NOT_LOGGED_IN') {
      setStatus('未登录，请先在 NavHub 登录', 'err');
      chrome.tabs.create({ url: server });
    } else if (e.message && e.message.includes('URL 已存在')) {
      setStatus('这个网站已经在导航里了', 'err');
    } else {
      setStatus('收藏失败：' + e.message, 'err');
    }
  } finally {
    saveBtn.disabled = false;
  }
});

// 显示当前页信息
(async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    document.querySelector('.card .title') && (document.querySelector('.card').innerHTML = '');
    // 用文本方式填充
    const card = document.querySelector('.card');
    card.innerHTML = '';
    const t = document.createElement('div');
    t.style.fontWeight = '500';
    t.textContent = tab.title || '未知页面';
    const u = document.createElement('div');
    u.className = 'url';
    u.textContent = tab.url || '';
    card.appendChild(t);
    card.appendChild(u);
  }
})();
