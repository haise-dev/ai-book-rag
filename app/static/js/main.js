// Main JavaScript file
console.log('AI Book Library loaded');

// Track saved books in memory for faster UI updates
let savedBooks = new Set();

// Load saved books on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadSavedBooks();
    updateAllSaveButtons();
});

// Load saved books from API
async function loadSavedBooks() {
    try {
        const response = await fetch('/api/saved-books');
        if (response.ok) {
            const data = await response.json();
            savedBooks = new Set(data.saved_books);
        }
    } catch (error) {
        console.error('Error loading saved books:', error);
    }
}

// Toggle save book function
async function toggleSaveBook(bookId, event) {
    // Prevent navigation if clicked from a link
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Find all buttons for this book
    const buttons = document.querySelectorAll(`[data-book-id="${bookId}"]`);
    
    // Disable buttons during request
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const response = await fetch(`/api/save-book/${bookId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update saved books set
            if (data.saved) {
                savedBooks.add(bookId);
            } else {
                savedBooks.delete(bookId);
            }
            
            // Update all buttons for this book
            updateBookButtons(bookId, data.saved);
            
            // Show notification
            showNotification(data.message, data.saved ? 'success' : 'info');
        } else {
            showNotification('Error saving book', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error saving book. Please try again.', 'error');
    } finally {
        // Re-enable buttons
        buttons.forEach(btn => btn.disabled = false);
    }
}

// Update all buttons for a specific book
function updateBookButtons(bookId, isSaved) {
    const buttons = document.querySelectorAll(`[data-book-id="${bookId}"]`);
    
    buttons.forEach(btn => {
        if (isSaved) {
            btn.innerHTML = '✅ Saved';
            btn.classList.remove('bg-blue-600', 'hover:bg-blue-700', 'text-white');
            btn.classList.add('bg-green-600', 'hover:bg-green-700', 'text-white');
        } else {
            btn.innerHTML = '💾 Save Book';
            btn.classList.remove('bg-green-600', 'hover:bg-green-700');
            btn.classList.add('bg-blue-600', 'hover:bg-blue-700', 'text-white');
        }
    });
}

// Update all save buttons on page load
function updateAllSaveButtons() {
    savedBooks.forEach(bookId => {
        updateBookButtons(bookId, true);
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 translate-x-full`;
    
    // Set color based on type
    const colors = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        info: 'bg-blue-500 text-white'
    };
    
    notification.classList.add(...colors[type].split(' '));
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Handle book actions from chat
window.handleChatBookAction = function(action, bookId) {
    if (action === 'view') {
        window.location.href = `/book/${bookId}`;
    } else if (action === 'save') {
        toggleSaveBook(bookId);
    }
};
