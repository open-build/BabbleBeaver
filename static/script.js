$(document).ready(function () {
  // get rid of chat history and number of tokens on page refresh
  sessionStorage.removeItem("messageHistory"); 
  sessionStorage.removeItem("totalUsedTokens");

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
         document.getElementById(x).disabled=should_disable
       })
    }

    disable_form(true)

    let sessionMessageHistory = sessionStorage.getItem("messageHistory");
    let userMessages = sessionMessageHistory !== null ? JSON.parse(sessionMessageHistory)["user"] : [];
    let botMessages = sessionMessageHistory !== null ? JSON.parse(sessionMessageHistory)["bot"] : [];
    let localMessageHistory = {user: userMessages, bot: botMessages}

    let sessionNumTokens = sessionStorage.getItem("totalUsedTokens");
    let localNumTokens = sessionNumTokens !== null ? JSON.parse(sessionNumTokens) : 0;

    $.ajax({
      url: '/chatbot',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({prompt: userMessage, history: localMessageHistory, tokens: localNumTokens}),
      success: function (data) {
        const {response: botMessage, usedTokens, updatedHistory} = data;
        
        // update client side with number of used tokens(included tokens used for the last user query and bot response)
        sessionStorage.setItem("totalUsedTokens", JSON.stringify(usedTokens));
        
        // if chat history was truncated because of token limit exceeded, needs to be updated on client side as well
        if (updatedHistory !== null) {
          localMessageHistory = updatedHistory;
          sessionStorage.setItem("messageHistory", JSON.stringify(localMessageHistory));
        }
        
        // update chat history
        localMessageHistory["user"].push(userMessage);
        localMessageHistory["bot"].push(botMessage);
        sessionStorage.setItem("messageHistory", JSON.stringify(localMessageHistory));

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
