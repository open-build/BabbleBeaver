# BabbleBeaver

Welcome to BabbleBeaver, an open-source conversational AI platform designed with privacy and flexibility in mind. BabbleBeaver leverages the power of Large Language Models (LLM) to provide customizable and isolated conversational agents, encapsulated in Docker containers for easy deployment and management.

## Overview

BabbleBeaver aims to democratize conversational AI, offering a plug-and-play solution that respects user privacy and data sovereignty. Built on top of FastAPI, BabbleBeaver facilitates rapid development and deployment of AI-powered chatbots with support for multiple, isolated LLM implementations.

## Installation


### To start FastAPI app on your local machine, follow these steps:

- Make sure you have Python installed on your machine. You can download and install Python from the official website: https://www.python.org/downloads/

- Create a new directory for your project and navigate to that directory using the command line.

- Create a new Python virtual environment. You can create a virtual environment by running the following command in the command line:

## VirtualENV
```bash
BabbleBeaver % virtualenv venv
/opt/homebrew/lib/python3.9/site-packages/setuptools/command/install.py:34: SetuptoolsDeprecationWarning: setup.py install is deprecated. Use build and pip and other standards-based tools.
  warnings.warn(
created virtual environment CPython3.9.17.final.0-64 in 510ms
  creator CPython3Posix(dest=/Users/greglind/Projects/buildly/insights/BabbleBeaver/venv, clear=False, no_vcs_ignore=False, global=False)
  seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/Users/greglind/Library/Application Support/virtualenv)
    added seed packages: pip==24.0, setuptools==69.1.1, wheel==0.42.0
  activators BashActivator,CShellActivator,FishActivator,NushellActivator,PowerShellActivator,PythonActivator
BabbleBeaver % source venv/bin/activate
(venv) BabbleBeaver % pip install -r requirements.txt
(venv) BabbleBeave % uvicorn main:app --reload
```

## Docker

```
docker build -t babble-beaver .
```
Activate the docker environment. and then run the fastapi app

```docker run -p 8000:8000 babble-beaver```

### Docker
```bash
git clone https://github.com/YourUsername/BabbleBeaver.git
cd BabbleBeaver
docker-compose up --build
```

Ensure Docker and Docker Compose are installed on your system before running these commands.

Using GitHub submodules is an efficient way to manage each Large Language Model (LLM) integration in your BabbleBeaver project. Submodules allow you to keep a Git repository as a subdirectory of another Git repository. This is ideal for including external dependencies, such as LLMs, in your project. Here’s how you can set it up:

### Step 1: Initialize Submodules in Your Project

First, you need to add each LLM integration as a submodule to your project. To do this, navigate to the root directory of your BabbleBeaver project in your terminal or command prompt, then use the following command for each LLM repository you want to include:

```bash
git submodule add <repository-url> path/to/submodule/directory
```

For example, if you have a specific LLM integration hosted at `https://github.com/someuser/LLM-integration.git` and you want to include it in the `integrations/llm` directory of your project, you would run:

```bash
git submodule add https://github.com/someuser/LLM-integration.git integrations/llm
```

Repeat this step for each LLM integration you want to include as a submodule.

### Step 2: Initialize and Update Submodules

After adding all necessary submodules, initialize and update them to ensure your local project reflects the correct state of those repositories:

```bash
git submodule init
git submodule update
```

This step ensures that the submodule directories are populated with the files from their respective repositories.

### Step 3: Commit Submodule Changes

Add the `.gitmodules` file and the newly added submodule directories to your project's repository and commit them:

```bash
git add .gitmodules path/to/submodule/directory
git commit -m "Added LLM integration submodules"
```

This commit tracks the submodule's current commit in your main project's repository.

### Step 4: Clone a Project with Submodules

If someone needs to clone your project including its submodules, they should use the `--recurse-submodules` option with the `git clone` command:

```bash
git clone --recurse-submodules https://github.com/open-build/BabbleBeaver.git
```

This ensures that all of the submodules are correctly initialized and checked out upon cloning the project.

### Step 5: Pull Updates for Submodules

To update all submodules to their latest commits, use the following commands:

```bash
git submodule update --remote --merge
```

This fetches the latest changes from the remote repositories and merges them into your project.

### Best Practices

- **Document Each Submodule**: Ensure you document the purpose and usage of each submodule in your project's README or documentation. This helps new contributors understand the architecture and dependencies of your project.
- **Regularly Update Submodules**: Keep your submodules up to date with their upstream repositories to incorporate bug fixes, security patches, and new features.
- **Version Pinning**: You might want to pin each submodule to a specific commit, tag, or branch that you know works well with your project to avoid unexpected changes breaking your application.

Using submodules allows you to maintain a clean separation between your core project and each LLM integration, facilitating easier updates, customization, and modular project management.

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
