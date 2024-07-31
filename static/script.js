$(document).ready(function () {
  // get rid of chat history and number of tokens on page refresh
  sessionStorage.removeItem("messageHistory"); 
  sessionStorage.removeItem("totalUsedTokens");

  const suggestedPrompts = $('#suggested-prompts');

  $.ajax({
    url: "/pre_user_prompt",
    type: "GET",
    success: function(data) {
      for (let i = 0; i < data.length; i++) {
        const btnElem = $('<button class="suggested-prompt-btn"></button>');
        btnElem.text(`${data[i]}`);
        suggestedPrompts.append(btnElem);
      }
    },
    error: function(error) {
      console.log(`Error: ${error}`)
    }
  })

  const chatForm = $('#chat-form');
  const chatMessages = $('#chat-messages');
  const userInput = $('#user-input');
  const submitButton = $('#submit-input');
  
  // delegating event to parent element since the buttons were dynamically generated
  suggestedPrompts.on("click", (e) => {
    userInput.val(e.target.textContent);
    submitButton.click();
  })

  chatForm.on('submit', (e) => {fetchResponse(e)});

  function fetchResponse(event) {
    event.preventDefault();

    const userMessage = userInput.val().trim();
    if (userMessage === '') return;

    suggestedPrompts.empty();

    const messageContainer = $('<div class="message user-message"></div>');
    const messageText = $('<p></p>').text(userMessage);
    messageContainer.append(messageText);
    chatMessages.append(messageContainer);

    // let's add the load dot animation to signal thinking....
    chatMessages.append('<div id="loader" class="loader"></div>')

    userInput.val('');

    disable_form = (should_disable) => {
       ['user-input','submit-input'].forEach(x => {
         document.getElementById(x).disabled=should_disable
       })
    }

    disable_form(true)

    let sessionMessageHistory = sessionStorage.getItem("messageHistory");
    let userMessages = sessionMessageHistory ? JSON.parse(sessionMessageHistory)["user"] : [];
    let botMessages = sessionMessageHistory ? JSON.parse(sessionMessageHistory)["bot"] : [];
    let localMessageHistory = {user: userMessages, bot: botMessages}

    let sessionNumTokens = sessionStorage.getItem("totalUsedTokens");
    let localNumTokens = sessionNumTokens ? JSON.parse(sessionNumTokens) : 0;

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
  }
});
