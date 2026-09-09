openai_gpt_54_models = [
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "openai.gpt-5.4",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "openai.gpt-5.4",
        "mantle_api": "responses",
    },
]

openai_gpt_5_5_models = [
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "openai.gpt-5.5",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "openai.gpt-5.5",
        "mantle_api": "responses",
    },
]

openai_gpt_6_astra_models = [   # GPT-6 Astra via Bedrock Converse
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "us.openai.gpt-6-astra",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "us.openai.gpt-6-astra",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "us.openai.gpt-6-astra",
    },
]

openai_gpt_5_6_sol_models = [   # GPT-5.6 Sol via Bedrock Converse
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-sol",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-sol",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-sol",
    },
]

openai_gpt_5_6_terra_models = [   # GPT-5.6 Terra via Bedrock Converse
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-terra",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-terra",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-terra",
    },
]

openai_gpt_5_6_luna_models = [   # GPT-5.6 Luna via Bedrock Converse
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-luna",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-luna",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "us.openai.gpt-5.6-luna",
    },
]


def get_model_info(model_name):
    models = []

    if model_name == "OpenAI GPT 5.4":
        models = openai_gpt_54_models
    elif model_name == "OpenAI GPT 5.5":
        models = openai_gpt_5_5_models
    elif model_name == "OpenAI GPT 6 Astra":
        models = openai_gpt_6_astra_models
    elif model_name == "OpenAI GPT 5.6 Sol":
        models = openai_gpt_5_6_sol_models
    elif model_name == "OpenAI GPT 5.6 Terra":
        models = openai_gpt_5_6_terra_models
    elif model_name == "OpenAI GPT 5.6 Luna":
        models = openai_gpt_5_6_luna_models

    return models


def get_stop_sequence(model_name):
    models = get_model_info(model_name)
    if not models:
        return ""
    return ""
