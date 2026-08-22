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

openai_gpt_5_6_sol_models = [   # GPT-5.6 Sol
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-sol",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-sol",
        "mantle_api": "responses",
    },
]

openai_gpt_5_6_terra_models = [   # GPT-5.6 Terra
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-terra",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-terra",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-terra",
        "mantle_api": "responses",
    },
]

openai_gpt_5_6_luna_models = [   # GPT-5.6 Luna
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-luna",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-luna",
        "mantle_api": "responses",
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "openai",
        "model_id": "openai.gpt-5.6-luna",
        "mantle_api": "responses",
    },
]


def get_model_info(model_name):
    models = []

    if model_name == "OpenAI GPT 5.4":
        models = openai_gpt_54_models
    elif model_name == "OpenAI GPT 5.5":
        models = openai_gpt_5_5_models
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
