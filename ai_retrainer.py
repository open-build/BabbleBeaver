import requests
from google.cloud import aiplatform
import os
import json
import PyPDF2
import docx
import openai

# ai_retrainer.py

class AIRetrainer:
    def retrain_with_api(self, api_endpoint, model_type, api_key):

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.get(api_endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if model_type == 'gemini':
                self.fine_tune_gemini(data)
            elif model_type == 'chatgpt':
                self.fine_tune_chatgpt(data)
            else:
                raise ValueError("Unsupported model type")
        else:
            raise Exception(f"Failed to retrieve data from API. Status code: {response.status_code}")

    def fine_tune_gemini(self, data):
        # Implementation for fine-tuning the Gemini model hosted on Google Cloud
        import google.auth

        # Authenticate with Google Cloud
        credentials, project = google.auth.default()

        # Initialize the AI Platform client
        client = aiplatform.gapic.JobServiceClient(credentials=credentials)

        # Define the fine-tuning job
        job = {
            "display_name": "fine_tune_gemini",
            "job_spec": {
                "worker_pool_specs": [
                    {
                        "machine_spec": {
                            "machine_type": "n1-standard-4"
                        },
                        "replica_count": 1,
                        "python_package_spec": {
                            "executor_image_uri": "gcr.io/cloud-aiplatform/training/tf-cpu.2-3:latest",
                            "package_uris": ["gs://your-bucket/path/to/your/package"],
                            "python_module": "trainer.task",
                            "args": ["--data", data]
                        }
                    }
                ]
            }
        }

        # Submit the job to AI Platform
        parent = f"projects/{project}/locations/us-central1"
        response = client.create_custom_job(parent=parent, custom_job=job)

        print(f"Job submitted. Job name: {response.name}")

    def fine_tune_chatgpt(self, data):
        # Implementation for fine-tuning the ChatGPT model

        # Set your OpenAI API key
        openai.api_key = os.getenv("OPENAI_API_KEY")

        # Prepare the data for fine-tuning
        training_data = []
        for item in data:
            training_data.append({
                "prompt": item["prompt"],
                "completion": item["completion"]
            })

        # Create a fine-tuning job
        response = openai.FineTune.create(
            training_file=training_data,
            model="davinci-codex",
            n_epochs=4
        )

        print(f"Fine-tuning job created. Job ID: {response['id']}")
    
    def retrain_with_documents(self, document_path, model_type):

        if not os.path.exists(document_path):
            raise FileNotFoundError(f"The document at {document_path} does not exist.")

        with open(document_path, 'r') as file:
            document_data = file.read()

        # Assuming the document contains JSON data
        if document_path.endswith('.pdf'):
            with open(document_path, 'rb') as file:
                reader = PyPDF2.PdfFileReader(file)
                document_data = ""
                for page in range(reader.numPages):
                    document_data += reader.getPage(page).extract_text()
        elif document_path.endswith('.docx'):
            doc = docx.Document(document_path)
            document_data = "\n".join([para.text for para in doc.paragraphs])
        elif document_path.endswith('.json'):
            with open(document_path, 'r') as file:
                document_data = file.read()
        else:
            raise ValueError("Unsupported document format. Only JSON, PDF and DOCX are supported.")

        data = json.loads(document_data)

        # Call the appropriate fine-tune method
        if model_type == 'gemini':
            self.fine_tune_gemini(data)
        elif model_type == 'chatgpt':
            self.fine_tune_chatgpt(data)
        else:
            raise ValueError("Unsupported model type")
