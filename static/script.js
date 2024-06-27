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

    // let's add the load dot animation to signal thinking....
    chatMessages.append('<div id="loader" class="loader"></div>')

    userInput.val('');

    disable_form = (should_disable) => {
       ['user-input','submit-input'].forEach(x => {
         state = should_disable ? 'DISABLE' : 'ENABLE'
         console.log(`trying to ${state} ${x}`)
         document.getElementById(x).disabled=should_disable
       })
    }

    disable_form(true)

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
      complete: function() {
        disable_form(false)
        document.getElementById("loader").remove()
      }
    });
  });
});
