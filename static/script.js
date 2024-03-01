$(document).ready(function () {
  const chatForm = $('#chat-form');
  const chatMessages = $('#chat-messages');
  const userInput = $('#user-input');

  chatForm.on('submit', function (event) {
    event.preventDefault();

    const userMessage = userInput.val().trim();
    if (userMessage === '') return;

    const messageContainer = $('<div class="message user-message"></div>');
    const messageText = $('<p></p>').text(userMessage);
    messageContainer.append(messageText);
    chatMessages.append(messageContainer);

    userInput.val('');

    $.ajax({
      url: '/chatbot',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ prompt: userMessage }),
      success: function (data) {
        const botMessage = data.response;

        const messageContainer = $('<div class="message bot-message"></div>');
        const messageText = $('<p></p>').text(botMessage);
        messageContainer.append(messageText);
        chatMessages.append(messageContainer);

        chatMessages.scrollTop(chatMessages.prop('scrollHeight'));
      },
      error: function (error) {
        console.error('Error:', error);
      },
    });
  });
});
