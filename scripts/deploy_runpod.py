import runpod
import json
import os
import requests
from typing import Dict, Optional

def initialize_runpod() -> None:
    """Initialize RunPod with API key."""
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        raise ValueError("RUNPOD_API_KEY environment variable is not set")
    runpod.api_key = api_key

def get_endpoints() -> list:
    """Retrieve all RunPod endpoints via GraphQL."""
    query = """
    query {
      myself {
        endpoints {
          id
          name
          templateId
        }
      }
    }
    """
    try:
        response = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {runpod.api_key}"}
        ).json()
        return response.get("data", {}).get("myself", {}).get("endpoints", [])
    except Exception as e:
        print(f"Error fetching endpoints: {e}")
        return []

def get_templates() -> list:
    """Retrieve all RunPod templates via GraphQL."""
    query = """
    query {
      myself {
        templates {
          id
          name
          imageName
          isServerless
        }
      }
    }
    """
    try:
        response = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {runpod.api_key}"}
        ).json()
        return response.get("data", {}).get("myself", {}).get("templates", [])
    except Exception as e:
        print(f"Error fetching templates: {e}")
        return []

def create_or_update_template(name: str, image_name: str) -> Optional[str]:
    """Create a new template or return the ID of an existing one."""
    templates = get_templates()  # Refresh templates list
    for template in templates:
        if template.get("name") == name and template.get("isServerless"):
            print(f"Found existing template '{name}' with ID: {template.get('id')}")
            return template.get("id")
    
    try:
        print(f"Creating new template '{name}' with image '{image_name}'")
        template = runpod.create_template(
            name=name,
            image_name=image_name,
            is_serverless=True,
            container_disk_in_gb=5
        )
        print(f"Created template '{name}' with ID: {template['id']}")
        return template["id"]
    except runpod.error.QueryError as e:
        if "Template name must be unique" in str(e):
            print(f"Template '{name}' already exists, fetching ID")
            templates = get_templates()  # Retry fetching templates
            for template in templates:
                if template.get("name") == name and template.get("isServerless"):
                    print(f"Retrieved existing template '{name}' with ID: {template.get('id')}")
                    return template.get("id")
            print(f"Error: Could not find existing template '{name}' despite duplicate name error")
            raise
        raise e

def main():
    """Deploy RunPod serverless endpoints."""
    try:
        initialize_runpod()

        # Get Docker image names from environment variables
        whisper_image = os.getenv("WHISPER_IMAGE")
        tts_image = os.getenv("TTS_IMAGE")
        llm_image = os.getenv("LLM_IMAGE")
        if not all([whisper_image, tts_image, llm_image]):
            raise ValueError("Missing one or more Docker image environment variables")

        # Get endpoints
        endpoints = get_endpoints()
        endpoint_ids = {"whisper": None, "tts": None, "llm": None}
        for endpoint in endpoints:
            name = endpoint.get("name")
            if name == "whisper-worker":
                endpoint_ids["whisper"] = endpoint.get("id")
            elif name == "tts-worker":
                endpoint_ids["tts"] = endpoint.get("id")
            elif name == "llm-worker":
                endpoint_ids["llm"] = endpoint.get("id")

        # Get or create template IDs
        template_ids = {
            "whisper": create_or_update_template("whisper-worker-template", whisper_image),
            "tts": create_or_update_template("tts-worker-template", tts_image),
            "llm": create_or_update_template("llm-worker-template", llm_image)
        }

        # Create or update endpoints
        responses = {}
        for worker in ["whisper", "tts", "llm"]:
            worker_name = f"{worker}-worker"
            template_id = template_ids[worker]
            endpoint_id = endpoint_ids[worker]
            try:
                if endpoint_id:
                    print(f"Updating endpoint '{worker_name}' with template ID: {template_id}")
                    responses[worker] = runpod.update_endpoint(
                        endpoint_id=endpoint_id,
                        template_id=template_id,
                        gpu_ids=["NVIDIA RTX A5000"],
                        name=worker_name,
                        active=True
                    )
                else:
                    print(f"Creating endpoint '{worker_name}' with template ID: {template_id}")
                    responses[worker] = runpod.create_endpoint(
                        name=worker_name,
                        template_id=template_id,
                        gpu_ids=["NVIDIA RTX A5000"],
                        workers_max=1
                    )
            except Exception as e:
                print(f"Error deploying {worker_name}: {e}")
                responses[worker] = {"error": str(e)}

        print(json.dumps(responses))
    except Exception as e:
        print(f"Error in main: {e}")
        exit(1)

if __name__ == "__main__":
    main()