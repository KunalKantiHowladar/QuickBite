document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Skip if we're not on the chat page
    if (!chatMessages) return;
    
    // Unique ID for this user session (use the user ID from the page if available)
    const userId = document.querySelector('meta[name="user-id"]')?.content || 'user_' + Math.random().toString(36).substring(2, 10);

    // Show typing indicator
    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'flex';
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    // Hide typing indicator
    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = 'none';
        }
    }

    // Add a message to the chat
    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        // Check if this is an Indian recipe response
        if (sender === 'bot' && (message.includes('Indian Cuisine') || message.includes('curry') || 
            message.includes('masala') || message.includes('tandoori'))) {
            messageDiv.classList.add('indian-recipe');
        }
        
        // Format message with proper HTML for recipes
        if (sender === 'bot' && message.includes('\n')) {
            message = message.replace(/\n/g, '<br>');
            
            // Highlight Indian terms
            const indianTerms = ['curry', 'masala', 'tandoori', 'naan', 'biryani', 'paneer', 
                               'samosa', 'chutney', 'indian', 'spicy', 'cumin', 'coriander',
                               'turmeric', 'garam masala', 'cardamom', 'ginger', 'ghee'];
            
            indianTerms.forEach(term => {
                const regex = new RegExp(`\\b${term}\\b`, 'gi');
                message = message.replace(regex, `<span class="recipe-highlight">$&</span>`);
            });
        }
        
        messageDiv.innerHTML = message;
        
        // Add time
        const timeSpan = document.createElement('span');
        timeSpan.classList.add('message-time');
        const now = new Date();
        timeSpan.textContent = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
        messageDiv.appendChild(timeSpan);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    // Send message to backend
    async function sendMessage(message) {
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message
                })
            });
            
            const data = await response.json();
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add bot message
            const botMessage = addMessage(data.response, 'bot');
            
            // Check if there's a follow-up message
            if (data.has_follow_up) {
                // Add a small delay before showing follow-up
                setTimeout(() => {
                    showTypingIndicator();
                    
                    setTimeout(() => {
                        hideTypingIndicator();
                        const followUpMessage = addMessage(data.follow_up, 'bot');
                    }, 1000);
                }, 500);
            }
            
        } catch (error) {
            hideTypingIndicator();
            addMessage("Sorry, I'm having trouble connecting. Please try again.", 'bot');
        }
    }

    // Event listeners
    if (sendBtn) {
    sendBtn.addEventListener('click', function() {
            const message = userInput.value.trim();
            if (message === '') return;
        sendMessage(message);
    });
    }

    if (userInput) {
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
                const message = userInput.value.trim();
                if (message === '') return;
                sendMessage(message);
            }
        });
    }
    
    // Ingredient chip click (if we're on the chat page)
    document.querySelectorAll('.ingredient-chip').forEach(chip => {
        chip.addEventListener('click', function() {
            const ingredient = this.getAttribute('data-ingredient');
            
            // If input is empty, just add the ingredient
            if (userInput.value.trim() === '') {
                userInput.value = ingredient;
            } 
            // If input already has content, append with comma
            else {
                // Check if the last character is already a comma
                if (userInput.value.trim().endsWith(',')) {
                    userInput.value = userInput.value.trim() + ' ' + ingredient;
                } else {
                    userInput.value = userInput.value.trim() + ', ' + ingredient;
                }
            }
            
            userInput.focus();
        });
    });
});
