# BabbleBeaver

Welcome to BabbleBeaver, an open-source conversational AI platform designed with privacy and flexibility in mind. BabbleBeaver leverages the power of Large Language Models (LLM) to provide customizable and isolated conversational agents, encapsulated in Docker containers for easy deployment and management.

## Overview

BabbleBeaver aims to democratize conversational AI, offering a plug-and-play solution that respects user privacy and data sovereignty. Built on top of FastAPI, BabbleBeaver facilitates rapid development and deployment of AI-powered chatbots with support for multiple, isolated LLM implementations.

## Installation

### Creating a .env file

To configure environment variables for BabbleBeaver, you need to create a `.env` file from the provided `example.env` file. Follow these steps:

1. Navigate to the project root directory where `example.env` is located.
2. Copy the `example.env` file to create a new `.env` file:
    ```bash
    cp example.env .env
    ```
3. Open the `.env` file in a text editor and update the values as needed. This file contains environment-specific variables such as API keys and configuration settings.

Make sure to keep the `.env` file secure and do not expose it publicly, as it may contain sensitive information.

To obtain the GOOGLE_APPLICATION_CREDENTIALS in the .env locate file inside the storage bucket: drunr_model_dataset, file is named: drunr-prod-97f378603f61.json. Place this file in an ./assets folder. Permission/Roles are managaed by vertexai_bot. 

To obtain the ENDPOINT_ID, the endpoint is found under the fine-tuned model in Model Garden

### Running the FastAPI application locally

- Make sure you have Python installed on your machine. You can download and install Python from the official website: https://www.python.org/downloads/

- Create a new directory for your project, then execute the following commands: `git clone https://github.com/YourUsername/BabbleBeaver.git
` followed by `cd BabbleBeaver` to navigate to the project root directory.

- Then execute the following commands which creates a virtual environment, activates it, then installs the necessary dependencies, followed by starting the application locally.

### VirtualENV
```bash
BabbleBeaver % virtualenv venv
BabbleBeaver % source venv/bin/activate
(venv) BabbleBeaver % pip install -r requirements.txt
(venv) BabbleBeave % uvicorn main:app --reload
```

- Make sure that if you're choosing to run the application using any of the following two methods, you have created and activated the virtual environment and have also installed all the necessary dependencies.

### Running the FastAPI application using Docker

To build the Docker image, then activate the docker environment and subsequently start the FastAPI server, run the following:
```
docker build -t babble-beaver .
docker run -p 8000:8000 babble-beaver
```

### Running the FastAPI application using Docker-Compose
```bash
docker-compose up --build
```

- **Ensure Docker and Docker Compose are installed on your system before running these commands.**

## Integrating a new model
At the time, BabbleBeaver is set up to work with LLMs available through several major proprietary providers such as OpenAI, Google, Mistral, Anthropic, and Cohere. It also supports LLM integration via open-source providers such as Ollama, OpenRouter, and HuggingFace. If you would like to integrate a specific model, please make sure to follow the given steps exactly:
1. Once you're in the project root directory, navigate to the `model_config.ini` configuration file in the `model_config` directory

2. For the new LLM which you'd like to use create a new entry in the configuration file exactly as follows with the following parameters. Keep in mind that none of the lines should be wrapped in quotes. The ones below are just to demonstrate how each line must be specified.
    - *"[`name of the model`]"* - The model name must be enclosed within square brackets and the name must correspond to the actual model ID specified by the provider (**REQUIRED**)
    - *"provider = `name of provider`"* (**REQUIRED**)
    - *"context_length = `the model's context window`"* - This needs to be an integer (**REQUIRED**)
    - *"api_key = `os.getenv("NAME OF API KEY IN .env file")`"* - If working with Ollama, replace the right side of this expression with any random string. (**REQUIRED**)
    - *"max_output_tokens = `maximum number of tokens this LLM should generate per output.`"* - This needs to be an integer (**OPTIONAL**)
    - *"temperature = `a floating point value dictating what kinds of outputs the LLM provides`"* - This value needs to be in the range `0 <= temperature <= 1` (**OPTIONAL**)

3. Once you've finished adding the model to the configuration file, head over to the `main.py` file.

4. Here, if you scroll down to the `/chatbot` endpoint, you will notice that you need to provide a few pieces of information pertaining to the model you want to use to get it up and running. The following are the ones you need to provide:
    - **Param 1**: `llm` - The name of the model as specified in the configuration file(**An error will be thrown if there's a mismatch**)
    - **Param 2**: `provider` - The name of the provider as specified in the configuration file(**An error will be thrown if there's a mismatch**)
    - **Param 3**: `tokenizer_function` - The tokenizer associated with this given model. **Make sure that this is a function**.
    - **Param 4**: `completion_function` - All you need to do is fill in the body of this pre-created function with the API call to be made to get a response from the model. **Make sure not to modify any of the parameters**.
    - **Param 5**: `use_initial_prompt` - Certain models may not support system instructions like `gemini-1.0-pro` for instance, although most models do. You still need to specify this parameter(**as a boolean**) in the function call to `set_model` to ensure that system instructions are passed in along with each API call made if you would like to do so.

**IMPORTANT NOTE**: There are some special considerations especially if you're integrating an Ollama model such as the following:
- You need to download Ollama locally and you can do so through this [link](https://ollama.com/download)
- Once you've downloaded Ollama, open up a terminal and first make sure to run the following command: `ollama pull model_name` where `model_name` corresponds to the model you want to integrate
- After you've pulled the model, run `ollama serve` to start Ollama up locally. After this point, you can use the model but keep in mind that when you're specifying the `completion_function` parameter in `main.py` and when using the OpenAI completions API to generate an output from this model, you specify the `base_url` parameter as well when instantiating the client, providing `http://localhost:11434/v1/` as the value

## Usage

After installation, BabbleBeaver can be accessed at `http://localhost:8000` by default. The API documentation, generated by FastAPI, is available at `http://localhost:8000/docs`.

## Architecture

BabbleBeaver adopts a modular architecture, with each conversational AI model implemented as a separate submodule. This allows for the easy addition, removal, or replacement of LLM implementations without affecting the core system.

- **Core System**: Built on FastAPI, the core handles API requests, routing, and integration with LLM submodules.
- **LLM Submodules**: Each LLM implementation is encapsulated within its Docker container, ensuring data isolation and security. Submodules communicate with the core system via RESTful APIs or message queues.
- **Data Layer**: For storing conversational logs, user data, and other relevant information, with support for encryption and GDPR compliance.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](/docs/CONTRIBUTING.md) for how to get involved. For setting up your development environment and the pull request process, refer to the guidelines.

## Community Guidelines

BabbleBeaver is committed to fostering an inclusive and safe community. Please read our [Community Guidelines](/docs/COMMUNITY_GUIDELINES.md) to understand our values and expectations.

# Product Vision Statement:
Our open-source project aims to create an accessible and robust conversational AI flexible software development platform. 

1. Select a Pre-trained Model
Choose a pre-trained model from Hugging Face's Transformers library that suits your needs for a conversational chatbot. Models like GPT (including GPT-2, GPT-3 if you have access through OpenAI's API, or GPT-Neo/GPT-J for fully open-source alternatives) are good starting points for building conversational agents.

2. Local Inference
Perform all inferences locally (or on your private cloud) to keep the data isolated. This means running the model on your own hardware without sending data out to third-party AI providers. Hugging Face Transformers library allows you to easily download pre-trained models and use them locally.

3. Fine-tuning (Optional)
If the pre-trained model doesn't meet your specific needs or you want to adapt it to your domain-specific conversations, you can fine-tune the model on your dataset. This step requires:

A custom dataset: Prepare a dataset representative of the conversations your chatbot will handle.
Compute resources: Fine-tuning LLMs can be resource-intensive, depending on the model size and dataset.
Keeping data isolated: Ensure your training process is conducted in a secure environment to maintain data privacy.


## License

BabbleBeaver is GPL-licensed. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project was inspired by the open-source community and the need for privacy-respecting AI tools.

## Contact

For questions, suggestions, or contributions, please open an issue in this repository or contact us at [team@open.build](mailto:team@open.build).


## Why GPL for BabbleBeaver?
Copyleft: The GPL is a strong copyleft license, which means that any modified versions of the project must also be distributed under the GPL. This ensures that the main codebase and any derivatives remain open source, promoting collaboration and improvement.
Compatibility with Other Licenses for Sub-Repositories: While the GPL itself is strict about the licensing of derived works, it allows for linking or interfacing with software under different licenses under certain conditions.
