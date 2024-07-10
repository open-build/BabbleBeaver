from enum import Enum
import os


class FineTuningConfig(Enum):
    """
    Enum for fine-tuning configuration options.
    """

    # Existing configuration options (replace with yours)
    BASE_MODEL_NAME = "base_model_name"
    DATA_PATH = "data_path"
    PRODUCT_ID = "product_id"
    EPOCHS = "epochs"
    LEARNING_RATE = "learning_rate"

    # New configuration options
    USE_ANONYMIZED_DATA = "use_anonymized_data"  # Flag for choosing between data or prompts
    PROMPTS_FILE = "prompts_file"  # Path to the file containing prompts (if applicable)


def get_config_from_env_vars():
    """
    Retrieves fine-tuning configuration from environment variables.
    """

    config = {}
    for option in FineTuningConfig:
        value = os.environ.get(option.value)
        if not value:
            raise ValueError(f"Environment variable '{option.value}' not set")
        config[option.value] = value
    return config



def get_config():
    """
    Retrieves fine-tuning configuration from environment variables or a file.
    TODO writh a funciton that loads from a file if needed
    """
    return get_config_from_env_vars()

