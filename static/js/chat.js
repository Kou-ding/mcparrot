import Sessions from './sessions.js';
import { playSound } from './sound.js';

const sessions = new Sessions();
const $ = (id) => document.getElementById(id);

class Chat {
    constructor(onStreamStart, onStreamEnd) {
        this.sending = false;
        this.abortController = null;
        this.onStreamStart = onStreamStart || (() => {});
        this.onStreamEnd = onStreamEnd || (() => {});
    }

    init() {
        const sendBtn = $('sendMessageBtn');
        const input = $('userInput');

        // Toggle between send and stop
        sendBtn?.addEventListener('click', () => this.toggleSendStop());
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.toggleSendStop();
            }
        });
        input?.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    }

    toggleSendStop() {
        if (this.sending) {
            this.stop();
        } else {
            this.send();
        }
    }

    async send() {
        const input = $('userInput');
        const sendBtn = $('sendMessageBtn');
        const message = input?.value.trim();
        if (!message) return;

        input.value = '';
        this.sending = true;

        // Send -> Stop
        if (sendBtn) {
            sendBtn.innerHTML = '<i class="fa-solid fa-stop"></i>';
            sendBtn.classList.add('stop-btn');
            sendBtn.title = 'Stop generation';
        }
        if (input) input.disabled = true;

        const parrotLogo = $('parrotLogo');
        parrotLogo?.classList.add('hidden');

        sessions.addMessage('user', message);
        this.onStreamStart();

        // Initialize AbortController
        this.abortController = new AbortController();
        let textDiv = null;
        let thinkingNode = null;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
                signal: this.abortController.signal // Attach signal to fetch
            });

            if (!response.ok || !response.body) {
                throw new Error(`Request failed: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const frames = buffer.split('\n\n');
                buffer = frames.pop();

                for (const frame of frames) {
                    const line = frame.trim();
                    if (!line.startsWith('data:')) continue;

                    const jsonStr = line.slice(5).trim();
                    if (!jsonStr) continue;

                    let event;
                    try {
                        event = JSON.parse(jsonStr);
                    } catch (e) {
                        console.error('Bad SSE frame:', jsonStr);
                        continue;
                    }

                    ({ textDiv, thinkingNode } = this.handleEvent(event, textDiv, thinkingNode));
                }
            }
            playSound("static/audio/success.wav");

        } catch (error) {
            // Handle the abort gracefully
            if (error.name === 'AbortError') {
                sessions.addMessage('assistant', '_Request stopped by user._');
            } else {
                console.error('Error streaming chat response:', error);
                sessions.addMessage('assistant', '_Something went wrong talking to the server._');
                playSound("static/audio/fail.wav");
            }
        } finally {
            this.onStreamEnd();
            if (textDiv) sessions.finishStreamingMessage(textDiv);
            this.resetUI();
        }
    }

    stop() {
        if (this.abortController) {
            this.abortController.abort(); // Trigger the GeneratorExit in Flask
            this.abortController = null;
        }
    }

    resetUI() {
        this.sending = false;
        const sendBtn = $('sendMessageBtn');
        const input = $('userInput');

        // Revert button Stop -> Send
        if (sendBtn) {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            sendBtn.classList.remove('stop-btn');
            sendBtn.title = 'Send message';
            sendBtn.disabled = false;
        }
        if (input) {
            input.disabled = false;
            input.focus();
        }
    }

    handleEvent(event, textDiv, thinkingNode) {
        switch (event.type) {
            case 'thinking_delta':
                if (!thinkingNode) thinkingNode = sessions.startStreamingThinking();
                sessions.appendToStreamingThinking(thinkingNode, event.text);
                break;
            case 'text_delta':
                if (!textDiv) textDiv = sessions.startStreamingMessage('assistant');
                sessions.appendToStreamingMessage(textDiv, event.text);
                break;
            case 'tool_use':
                if (textDiv) { sessions.finishStreamingMessage(textDiv); textDiv = null; }
                thinkingNode = null;
                sessions.addToolUse(event.name, event.input);
                break;
            case 'tool_result':
                sessions.addToolResult(event.content);
                break;
            case 'error':
                sessions.addMessage('assistant', `_Error: ${event.message}_`);
                break;
            case 'done':
                if (textDiv) { sessions.finishStreamingMessage(textDiv); textDiv = null; }
                break;
            default:
                console.warn('Unknown SSE event type:', event.type);
        }
        return { textDiv, thinkingNode };
    }
}

export default Chat;
