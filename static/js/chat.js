import Sessions from './sessions.js';
import { playSound } from './sound.js';

const sessions = new Sessions();

const $ = (id) => document.getElementById(id);

class Chat {
    constructor(onStreamStart, onStreamEnd) {
        this.sending = false;
        this.onStreamStart = onStreamStart || (() => {});
        this.onStreamEnd = onStreamEnd || (() => {});
    }

    init() {
        const sendBtn = $('sendMessageBtn');
        const input = $('userInput');

        sendBtn?.addEventListener('click', () => this.send());
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });
        input?.addEventListener('input', function () {
            this.style.height = 'auto'; // Reset height so it can shrink if text is deleted
            this.style.height = this.scrollHeight + 'px'; // Expand to fit the text
        });
    }

    async send() {
        if (this.sending) return;

        const input = $('userInput');
        const sendBtn = $('sendMessageBtn');
        const message = input?.value.trim();
        if (!message) return;

        // Lock UI to prevent double submissions
        input.value = '';
        this.sending = true;
        if (sendBtn) sendBtn.disabled = true;
        if (input) input.disabled = true;

        const parrotLogo = $('parrotLogo');
        parrotLogo?.classList.add('hidden');

        sessions.addMessage('user', message);

        // Start polling exactly when the request begins
        this.onStreamStart();

        input.value = '';
        this.sending = true;

        // State for the current in-flight assistant turn. A single /chat call
        // can contain several LLM turns (tool use loops), each with its own
        // streamed text, so we track the "current" bubble/thinking node and
        // reset them whenever a new one starts.
        let textDiv = null;
        let thinkingNode = null;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
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

                // SSE frames are separated by a blank line
                const frames = buffer.split('\n\n');
                buffer = frames.pop(); // last chunk may be incomplete

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
            // If no error was caught
            playSound("static/audio/success.wav");

        } catch (error) {
            console.error('Error streaming chat response:', error);
            sessions.addMessage('assistant', '_Something went wrong talking to the server._');
            playSound("static/audio/fail.wav");
        } finally {
            // Stop polling as soon as the stream finishes or fails
            this.onStreamEnd();
            if (textDiv) sessions.finishStreamingMessage(textDiv);
            this.sending = false;
            if (sendBtn) sendBtn.disabled = false;
            if (input) {
                input.disabled = false;
                input.focus(); // Automatically focus back to input for the next message
            }
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
                // A tool call always ends the current text/thinking bubble for this turn.
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
