import Settings from './settings.js';

const $ = (id) => document.getElementById(id);
const settings = new Settings();

class Sessions {
    // Initialization
    async init(){
        await this.getAllSessions();
        await this.getCurrentSession();
    }
    // === Populate dropdown ===
    async getAllSessions() {
        const sessionSelect = $('sessionSelect');
        if (!sessionSelect) return;

        try {
            // Fetch available sessions
            const response = await fetch('/get-sessions');
            const data = await response.json();

            // Clear existing options
            sessionSelect.innerHTML = '';

            // Populate dropdown
            data.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session;
                option.textContent = session;
                sessionSelect.appendChild(option);
            });  
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    // === Active session ===
    async getCurrentSession() {
        const sessionSelect = $('sessionSelect');
        const selectedSession = $('selectedSession');
        if (!sessionSelect) return;

        try {
            const currentSession = await settings.getSetting('session');
            if (currentSession) {
                sessionSelect.value = currentSession;
                if (selectedSession) selectedSession.textContent = currentSession;
                await this.displaySession(currentSession);
            }
        } catch (error) {
            console.error('Error loading current session:', error);
        }   
    }

    // === Session rendering ===
    async displaySession(sessionFile) {
        const messagesContainer = $('messagesContainer');
        if (!messagesContainer) return;
        
        messagesContainer.innerHTML = ''; 
        const messages = await this.loadSession(sessionFile);
        const parrotLogo = $('parrotLogo');
        
        parrotLogo?.classList.toggle('hidden', messages.length > 0);
        
        messages.forEach(msg => {
            if (typeof msg.content === 'string') {
                this.addMessage(msg.role, msg.content);
            } else if (Array.isArray(msg.content)) {
                msg.content.forEach(item => {
                    if (item.type === 'text') this.addMessage(msg.role, item.text);
                    else if (item.type === 'thinking') this.addThinking(item.thinking, item.signature);
                    else if (item.type === 'tool_use') this.addToolUse(item.name, item.input);
                    else if (item.type === 'tool_result') this.addToolResult(item.content);
                });
            }
        });
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // === Load session from file ===
    async loadSession(sessionFile) {
        try {
            const response = await fetch(`/sessions/${sessionFile}`);
            const text = await response.text();
            if (!text || text.trim() === '' || text.trim() === '[]') return [];
            return JSON.parse(text);
        } catch (error) {
            console.error('Error loading session:', error);
            return [];
        }
    }

    // === Messages ===
    addMessage(role, content) {
        const messagesContainer = $('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);
        messageDiv.innerHTML = window.marked ? marked.parse(content || '') : (content || '');
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageDiv;
    }

    startStreamingMessage(role = 'assistant') {
        const messagesContainer = $('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role, 'streaming');
        messageDiv.dataset.buffer = '';
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageDiv;
    }

    appendToStreamingMessage(messageDiv, textChunk) {
        if (!messageDiv) return;
        messageDiv.dataset.buffer = (messageDiv.dataset.buffer || '') + textChunk;
        messageDiv.innerHTML = window.marked ? marked.parse(messageDiv.dataset.buffer) : messageDiv.dataset.buffer;
        const messagesContainer = $('messagesContainer');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    finishStreamingMessage(messageDiv) {
        messageDiv?.classList.remove('streaming');
    }

    ensureTraceGroup() {
        const messagesContainer = $('messagesContainer');
        const last = messagesContainer.lastElementChild;
        if (last && last.classList.contains('trace-group')) return last;
        
        const group = document.createElement('div');
        group.classList.add('trace-group');
        group.dataset.count = '0';
        messagesContainer.appendChild(group);
        return group;
    }

    addTraceNode(type, tag, previewText, bodyHtml) {
        const group = this.ensureTraceGroup();
        const count = parseInt(group.dataset.count || '0', 10) + 1;
        group.dataset.count = String(count);
        const hexIndex = '0x' + count.toString(16).padStart(2, '0').toUpperCase();

        const node = document.createElement('div');
        node.classList.add('trace-node', type, 'collapsed');
        node.innerHTML = `
            <div class="trace-row">
                <span class="trace-dot"></span>
                <span class="trace-index">${hexIndex}</span>
                <span class="trace-tag">${tag}</span>
                <span class="trace-preview">${this.escapeHtml(previewText || '')}</span>
                <span class="trace-chevron">&#8250;</span>
            </div>
            <div class="trace-body">${bodyHtml}</div>
        `;
        
        // Replaced inline JS with proper event listener
        node.querySelector('.trace-row').addEventListener('click', () => {
            node.classList.toggle('collapsed');
        });

        group.appendChild(node);
        $('messagesContainer').scrollTop = $('messagesContainer').scrollHeight;
        return node;
    }

    addThinking(thinking, signature) {
        const preview = this.truncate((thinking || '').replace(/\s+/g, ' ').trim(), 70);
        const body = `
            <div class="trace-markdown">${window.marked ? marked.parse(thinking || '') : (thinking || '')}</div>
            ${signature ? `<div class="trace-signature">${this.escapeHtml(signature)}</div>` : ''}
        `;
        return this.addTraceNode('thinking', 'Thinking', preview, body);
    }

    startStreamingThinking() {
        const node = this.addTraceNode('thinking', 'Thinking', '', '<div class="trace-markdown"></div>');
        node.dataset.buffer = '';
        return node;
    }

    appendToStreamingThinking(node, textChunk) {
        if (!node) return;
        node.dataset.buffer = (node.dataset.buffer || '') + textChunk;
        node.querySelector('.trace-preview').textContent = this.truncate(node.dataset.buffer.replace(/\s+/g, ' ').trim(), 70);
        node.querySelector('.trace-markdown').innerHTML = window.marked ? marked.parse(node.dataset.buffer) : node.dataset.buffer;
    }

    addToolUse(name, input) {
        const body = `<pre class="trace-code">${this.highlightJSON(input)}</pre>`;
        return this.addTraceNode('toolcall', 'Tool call', name, body);
    }

    addToolResult(content) {
        const text = (content || []).map(c => c.text || '').join('\n');
        const preview = this.truncate(text.replace(/\s+/g, ' ').trim(), 70);
        const body = `<pre class="trace-code">${this.escapeHtml(text)}</pre>`;
        return this.addTraceNode('result', 'Result', preview, body);
    }

    truncate(text, len) {
        if (!text) return '';
        return text.length > len ? text.slice(0, len) + '…' : text;
    }

    escapeHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    highlightJSON(input) {
        const json = this.escapeHtml(JSON.stringify(input, null, 2));
        return json
            .replace(/"([^"]+)":/g, '<span class="tk-key">"$1"</span>:')
            .replace(/: "([^"]*)"/g, ': <span class="tk-str">"$1"</span>')
            .replace(/: (-?\d+\.?\d*)/g, ': <span class="tk-num">$1</span>')
            .replace(/: (true|false|null)/g, ': <span class="tk-bool">$1</span>');
    }
}

export default Sessions;