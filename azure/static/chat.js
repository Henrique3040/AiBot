async function sendMessage() {
    const userInput = document.getElementById('userInput').value;
    if (!userInput) return;

    // Display user's message
    displayMessage(userInput, 'user');

    // Send message to Flask server
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userInput })
    });

    const data = await response.json();
    const aiMessage = data.message;

    // Display AI's message
    displayMessage(aiMessage, 'ai');

    // Clear input
    document.getElementById('userInput').value = '';
}

function displayMessage(message, sender) {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message ${sender}`;
    messageContainer.textContent = message;

    const messagesDiv = document.getElementById('messages');
    messagesDiv.appendChild(messageContainer);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
