// AI Chat Widget JavaScript
// Handles SSE connection and chat interactions

class AIBookChat {
    constructor() {
        this.sessionId = this.getSessionId();
        this.eventSource = null;
        this.isConnected = false;
        this.processedMessages = new Set();
        this.initializeElements();
        this.setupEventListeners();
        
        // Auto-connect when widget is opened
        const widget = document.getElementById('chat-widget');
        if (widget && !widget.classList.contains('hidden')) {
            this.connectToSSE();
        }
    }

    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }

    initializeElements() {
        this.chatWidget = document.getElementById('chat-widget');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-button');
        this.toggleButton = document.getElementById('chat-toggle');
        this.clearButton = document.getElementById('clear-chat');
        this.connectionStatus = document.getElementById('connection-status');
        this.navbarChatButton = document.querySelector('a[href="#"][onclick*="chat"]');
    }

    setupEventListeners() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleChat();
            });
        }

        if (this.navbarChatButton) {
            this.navbarChatButton.onclick = (e) => {
                e.preventDefault();
                this.toggleChat();
                return false;
            };
        }

        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.chatInput) {
            this.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (this.clearButton) {
            this.clearButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearChat();
            });
        }
    }

    toggleChat() {
        if (this.chatWidget) {
            this.chatWidget.classList.toggle('hidden');
            
            if (!this.chatWidget.classList.contains('hidden') && !this.isConnected) {
                this.connectToSSE();
            }
            
            if (!this.chatWidget.classList.contains('hidden') && this.chatInput) {
                this.chatInput.focus();
            }
        }
    }

    connectToSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        console.log('Connecting to chat stream...');
        this.eventSource = new EventSource(`/api/chat/stream/${this.sessionId}`);

        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus('connected');
            console.log('Connected to chat stream');
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this.updateConnectionStatus('error');
            this.isConnected = false;
            
            setTimeout(() => {
                if (!this.isConnected && this.chatWidget && !this.chatWidget.classList.contains('hidden')) {
                    this.connectToSSE();
                }
            }, 5000);
        };
    }

    handleMessage(data) {
        if (data.type === 'connected') {
            console.log('Chat connected successfully');
            return;
        }

        // Create unique key for this message state
        const messageKey = `${data.id}_${data.status || 'initial'}`;
        
        // Skip if we already processed this exact message state
        if (this.processedMessages.has(messageKey)) {
            console.log('Skipping already processed:', messageKey);
            return;
        }
        
        this.processedMessages.add(messageKey);
        
        const existingMsg = document.querySelector(`[data-message-id="${data.id}"]`);
        
        if (existingMsg) {
            // Update existing message only
            const contentEl = existingMsg.querySelector('.message-content');
            if (contentEl) {
                if (data.status === 'thinking') {
                    contentEl.innerHTML = '<span class="thinking-dots"></span>';
                } else {
                    contentEl.innerHTML = this.parseMarkdown(data.content);
                    existingMsg.classList.remove('thinking');
                }
            }
        } else {
            // Add new message
            this.addMessageToChat(data);
        }

        if (data.actions) {
            this.handleActions(data.actions);
        }
    }

    addMessageToChat(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role} ${message.status === 'thinking' ? 'thinking' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = message.role === 'user' ? '👤' : '🤖';

        const content = document.createElement('div');
        content.className = 'message-content';
        
        if (message.status === 'thinking') {
            content.innerHTML = '<span class="thinking-dots"></span>';
        } else {
            content.innerHTML = this.parseMarkdown(message.content);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    parseMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    handleActions(actions) {
        if (actions.type === 'book_results') {
            const bookCardsDiv = document.createElement('div');
            bookCardsDiv.className = 'book-results';
            
            actions.books.forEach(book => {
                const bookCard = document.createElement('div');
                bookCard.className = 'mini-book-card';
                bookCard.innerHTML = `
                    <h4>${book.title}</h4>
                    <p>by ${book.author}</p>
                    <a href="/book/${book.id}" class="view-link">View Details</a>
                `;
                bookCardsDiv.appendChild(bookCard);
            });
            
            this.chatMessages.appendChild(bookCardsDiv);
            this.scrollToBottom();
        } else if (actions.type === 'save_book') {
            this.saveBook(actions.book_id);
        }
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        this.chatInput.value = '';

        this.addMessageToChat({
            id: 'temp_' + Date.now(),
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });

        try {
            const params = new URLSearchParams({
                message: message,
                session_id: this.sessionId
            });

            const response = await fetch(`/api/chat/send?${params}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            const data = await response.json();
            console.log('Message sent successfully:', data);

        } catch (error) {
            console.error('Error sending message:', error);
            const tempMsg = document.querySelector('[data-message-id^="temp_"]');
            if (tempMsg) tempMsg.remove();
            
            this.addMessageToChat({
                id: 'error_' + Date.now(),
                role: 'assistant',
                content: 'Sorry, I encountered an error sending your message. Please try again.',
                status: 'error'
            });
        }
    }

    async saveBook(bookId) {
        try {
            const response = await fetch(`/api/books/${bookId}/save`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                this.showNotification('Book saved to your list!', 'success');
            }
        } catch (error) {
            console.error('Error saving book:', error);
            this.showNotification('Failed to save book', 'error');
        }
    }

    async clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            try {
                const response = await fetch(`/api/chat/clear/${this.sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    this.chatMessages.innerHTML = '';
                    this.processedMessages.clear();
                    this.addWelcomeMessage();
                }
            } catch (error) {
                console.error('Error clearing chat:', error);
                this.showNotification('Failed to clear chat', 'error');
            }
        }
    }

    addWelcomeMessage() {
        this.addMessageToChat({
            id: 'welcome',
            role: 'assistant',
            content: 'Hello! I\'m your AI Book Assistant. How can I help you find your next great read?',
            timestamp: new Date().toISOString()
        });
    }

    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    updateConnectionStatus(status) {
        if (this.connectionStatus) {
            this.connectionStatus.className = `connection-status ${status}`;
            this.connectionStatus.textContent = status === 'connected' ? '🟢' : '🔴';
        }
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (!window.aiBookChat) {
        console.log('Initializing AI Book Chat...');
        window.aiBookChat = new AIBookChat();
    }
});
