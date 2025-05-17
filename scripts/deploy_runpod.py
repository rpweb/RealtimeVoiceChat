import runpod
import json
import os
import sys
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
        if "errors" in response:
            print(f"GraphQL errors in get_endpoints: {json.dumps(response['errors'], indent=2)}", file=sys.stderr)
        return response.get("data", {}).get("myself", {}).get("endpoints", [])
    except Exception as e:
        print(f"Error fetching endpoints: {e}", file=sys.stderr)
        return []

def get_templates() -> list:
    """Retrieve all RunPod templates via GraphQL."""
    query = """
    query {
      myself {
        podTemplates {
          id
          name
          isServerless
          imageName
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
        if "errors" in response:
            print(f"GraphQL errors in get_templates: {json.dumps(response['errors'], indent=2)}", file=sys.stderr)
        templates = response.get("data", {}).get("myself", {}).get("podTemplates", [])
        print(f"Templates fetched: {json.dumps(templates, indent=2)}", file=sys.stderr)
        return templates
    except Exception as e:
        print(f"Error fetching templates: {e}", file=sys.stderr)
        return []

def create_or_update_template(name: str, image_name: str) -> Optional[str]:
    """Create a new template or return the ID of an existing one with valid imageName."""
    templates = get_templates()
    print(f"Searching for template '{name}'", file=sys.stderr)
    for template in templates:
        if template.get("name") == name:
            is_serverless = template.get("isServerless", False)
            current_image = template.get("imageName", "")
            print(f"Found template '{name}' with ID: {template.get('id')}, isServerless: {is_serverless}, imageName: {current_image}", file=sys.stderr)
            if not is_serverless:
                raise ValueError(f"Template '{name}' is not serverless")
            if current_image.startswith("$") or not current_image:
                raise ValueError(f"Template '{name}' has invalid imageName '{current_image}'. Update to '{image_name}' in RunPod console.")
            return template.get("id")
    
    try:
        print(f"Creating new template '{name}' with image '{image_name}'", file=sys.stderr)
        template = runpod.create_template(
            name=name,
            image_name=image_name,
            is_serverless=True,
            container_disk_in_gb=5
        )
        print(f"Created template '{name}' with ID: {template['id']}", file=sys.stderr)
        return template["id"]
    except runpod.error.QueryError as e:
        print(f"Error creating template '{name}': {str(e)}", file=sys.stderr)
        if "Template name must be unique" in str(e):
            raise ValueError(f"Template '{name}' exists with invalid imageName. Update it in RunPod console.")
        raise e
    except Exception as e:
        print(f"Unexpected error creating template '{name}': {str(e)}", file=sys.stderr)
        raise

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
                    print(f"Updating endpoint '{worker_name}' with ID: {endpoint_id}", file=sys.stderr)
                    responses[worker] = runpod.update_endpoint_template(
                        endpoint_id=endpoint_id,
                        template_id=template_id
                    )
                else:
                    print(f"Creating new endpoint '{worker_name}' with template ID: {template_id}", file=sys.stderr)
                    responses[worker] = runpod.create_endpoint(
                        name=worker_name,
                        template_id=template_id,
                        gpu_ids=["NVIDIA RTX A5000"],
                        workers_max=1
                    )
            except Exception as e:
                print(f"Error deploying {worker_name}: {e}", file=sys.stderr)
                responses[worker] = {"error": str(e)}

        # Output JSON to stdout
        print(json.dumps(responses))
    except Exception as e:
        print(f"Error in main: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()