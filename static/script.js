$(document).ready(function () {
  // sessionStorage.removeItem("messageHistory"); 
  // sessionStorage.removeItem("totalUsedTokens");

  const suggestedPrompts = $('#suggested-prompts');
  const chatForm = $('#chat-form');
  const chatMessages = $('#chat-messages');
  const userInput = $('#user-input');
  const submitButton = $('#submit-input');

  $.ajax({
    url: "/pre_user_prompt",
    type: "POST",
    data: JSON.stringify({session_id: '12344412'}), // pass session_id from react comp
    success: function(data) {
      prompt_history = data['prompt_history']
      suggested_prompts = Array(data['suggested_prompts'])
      for (let i = 0; i < suggested_prompts[0].length; i++) {
        const btnElem = $('<button class="suggested-prompt-btn"></button>');
        btnElem.text(`${suggested_prompts[0][i]}`);
        suggestedPrompts.append(btnElem);
      }

      for (let i = 0; i < prompt_history.length; i++) {
        const messageUserContainer = $('<div class="message user-message"></div>');
        const messageBotContainer = $('<div class="message bot-message"></div>');
        if (prompt_history[i].sender === 'user') {
          console.log("user: ", prompt_history[i].message)
          messageUserContainer.append($('<p></p>').text(prompt_history[i].message));
          chatMessages.append(messageUserContainer);
        }
        if (prompt_history[i].sender === 'bot') {
          console.log("bot: ", prompt_history[i].message)
          messageBotContainer.append($('<p></p>').text(prompt_history[i].message));
          chatMessages.append(messageBotContainer);
        }
      }
    },
    error: function(error) {
      console.log(`Error: ${error}`)
    }
  })
  
  suggestedPrompts.on("click", (e) => {
    console.log(e.target.textContent)
    userInput.val(e.target.textContent);
    submitButton.click();
  })

  chatForm.on('submit', (e) => {fetchResponse(e)});

  function fetchResponse(event) {
    event.preventDefault();

    const userMessage = userInput.val().trim();
    if (userMessage === '') return;

    suggestedPrompts.empty();

    chatMessages.append('<div id="loader" class="loader"></div>')

    userInput.val('');

    disable_form = (should_disable) => {
       ['user-input','submit-input'].forEach(x => {
         document.getElementById(x).disabled=should_disable
       })
    }

    disable_form(true)
    let sessionMessageHistory = sessionStorage.getItem("history");
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
        console.log("data: ", data);
        const botMessage = data.history;
        const kaiMessage = data.kai_response;
        const rawPrompt = data.user_prompt;
        const fullPrompt = data.prompt;
        const usedTokens = data.tokens;
        const modelVersion = data.model_version;
        const updatedHistory = data.model_version;

        if (botMessage !== "Sorry... An error occurred.") {
          sessionStorage.setItem("totalUsedTokens", JSON.stringify(usedTokens));
          
          // if chat history was truncated because of token limit exceeded, needs to be updated on client side as well
          // if (updatedHistory !== null) {
          //   localMessageHistory = updatedHistory;
          //   sessionStorage.setItem("messageHistory", JSON.stringify(localMessageHistory));
          // }
        }

        const messageUserContainer = $('<div class="message user-message"></div>');
        const messageBotContainer = $('<div class="message bot-message"></div>');
        messageUserContainer.append($('<p></p>').text(rawPrompt));
        chatMessages.append(messageUserContainer);
        messageBotContainer.append($('<p></p>').text(kaiMessage));
        chatMessages.append(messageBotContainer);
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