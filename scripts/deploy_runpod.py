import runpod
import json
import os
import sys
import requests
from typing import Dict, Optional, List
from time import sleep
from requests.exceptions import RequestException

def initialize_runpod() -> None:
    """Initialize RunPod with API key and validate."""
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        raise ValueError("RUNPOD_API_KEY environment variable is not set")
    runpod.api_key = api_key
    test_query = """query { myself { id } }"""
    try:
        response = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": test_query},
            headers={"Authorization": f"Bearer {api_key}"}
        ).json()
        if "errors" in response:
            raise ValueError(f"Invalid API key: {json.dumps(response['errors'], indent=2)}")
    except Exception as e:
        raise ValueError(f"API key validation failed: {e}")

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
        for template in templates:
            print(f"Template: name={template.get('name')}, id={template.get('id')}, imageName={template.get('imageName')}", file=sys.stderr)
        return templates
    except Exception as e:
        print(f"Error fetching templates: {e}", file=sys.stderr)
        return []

def get_volumes() -> list:
    """Retrieve all RunPod network volumes via GraphQL."""
    query = """query { myself { networkVolumes { id name } } }"""
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.runpod.io/graphql",
                json={"query": query},
                headers={"Authorization": f"Bearer {runpod.api_key}"}
            ).json()
            if "errors" in response:
                print(f"Attempt {attempt + 1}/3: GraphQL errors in get_volumes: {json.dumps(response['errors'], indent=2)}", file=sys.stderr)
                if attempt < 2:
                    sleep(5)
                    continue
                print("Failed to fetch volumes. Proceeding without validation.", file=sys.stderr)
                return []
            volumes = response.get("data", {}).get("myself", {}).get("networkVolumes", [])
            print(f"Found volumes: {[{v['id']: v['name']} for v in volumes]}", file=sys.stderr)
            return volumes
        except Exception as e:
            print(f"Attempt {attempt + 1}/3: Error fetching volumes: {e}", file=sys.stderr)
            if attempt < 2:
                sleep(5)
                continue
            print("Failed to fetch volumes. Proceeding without validation.", file=sys.stderr)
            return []

def create_or_update_template(
    name: str, 
    image_name: str, 
    env_vars: Dict[str, str] = None,
    volume_id: str = None,
    retries: int = 3,
    delay: int = 5
) -> Optional[str]:
    """Create a new template or return the ID of an existing one with valid imageName."""
    templates = get_templates()
    print(f"Searching for template '{name}' with image '{image_name}'", file=sys.stderr)
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
    
    print(f"Creating new template '{name}' with image '{image_name}'", file=sys.stderr)
    
    # First try the SDK method (simpler approach)
    try:
        # Create the template with basic settings
        template = runpod.create_template(
            name=name,
            image_name=image_name,
            is_serverless=True,
            container_disk_in_gb=5
        )
        template_id = template["id"]
        print(f"Created template with SDK, ID: {template_id}", file=sys.stderr)
        
        # If we have env vars or volume, update the template
        if env_vars or volume_id:
            print(f"Updating template with env vars and volume", file=sys.stderr)
            if volume_id:
                # Update with volume mount
                try:
                    # Use GraphQL for volume mounting
                    mutation = """
                    mutation ($id: ID!, $input: PodTemplateUpdateInput!) {
                        podTemplateUpdate(id: $id, input: $input) {
                            id
                        }
                    }
                    """
                    variables = {
                        "id": template_id,
                        "input": {
                            "volumeMounts": [{"volumeId": volume_id, "mountPath": "/workspace"}]
                        }
                    }
                    
                    # Add env vars if present
                    if env_vars:
                        variables["input"]["env"] = [{"key": k, "value": v} for k, v in env_vars.items()]
                        
                    response = requests.post(
                        "https://api.runpod.io/graphql",
                        json={"query": mutation, "variables": variables},
                        headers={"Authorization": f"Bearer {runpod.api_key}"}
                    ).json()
                    
                    if "errors" in response:
                        print(f"Warning: Error updating template: {json.dumps(response['errors'], indent=2)}", file=sys.stderr)
                        # Continue anyway since template was created
                except Exception as update_error:
                    print(f"Warning: Failed to update template with volume: {update_error}", file=sys.stderr)
                    # Continue anyway since template was created
            elif env_vars:
                # Only update env vars, which the SDK supports directly
                try:
                    runpod.update_template(
                        template_id=template_id,
                        env=env_vars
                    )
                except Exception as env_error:
                    print(f"Warning: Failed to update template with env vars: {env_error}", file=sys.stderr)
        
        return template_id
    
    except Exception as sdk_error:
        print(f"SDK template creation failed: {sdk_error}, trying GraphQL method", file=sys.stderr)
        
        # Fall back to GraphQL method
        for attempt in range(retries):
            try:
                # Prepare GraphQL mutation
                mutation = """
                mutation ($input: PodTemplateInput!) {
                    podTemplateSave(input: $input) {
                        id
                    }
                }
                """
                
                variables = {
                    "input": {
                        "name": name,
                        "imageName": image_name,
                        "isServerless": True,
                        "containerDiskSizeGB": 5
                    }
                }
                
                # Add env vars if present
                if env_vars:
                    variables["input"]["env"] = [{"key": k, "value": v} for k, v in env_vars.items()]
                
                # Add volume mount if present
                if volume_id:
                    variables["input"]["volumeMounts"] = [{"volumeId": volume_id, "mountPath": "/workspace"}]
                
                # Try to authenticate with Docker Hub if credentials are available
                if os.getenv("DOCKERHUB_USERNAME") and os.getenv("DOCKERHUB_PASSWORD"):
                    variables["input"]["dockerCredentials"] = {
                        "username": os.getenv("DOCKERHUB_USERNAME"),
                        "password": os.getenv("DOCKERHUB_PASSWORD")
                    }
                
                # Execute GraphQL mutation
                response = requests.post(
                    "https://api.runpod.io/graphql",
                    json={"query": mutation, "variables": variables},
                    headers={"Authorization": f"Bearer {runpod.api_key}"}
                ).json()
                
                # Handle errors
                if "errors" in response:
                    error_msg = response.get("errors", [{}])[0].get("message", "Unknown error")
                    print(f"Attempt {attempt + 1}/{retries}: GraphQL error: {error_msg}", file=sys.stderr)
                    if attempt < retries - 1:
                        print(f"Retrying in {delay} seconds...", file=sys.stderr)
                        sleep(delay)
                        continue
                    raise Exception(error_msg)
                
                # Extract template ID
                template_id = response.get("data", {}).get("podTemplateSave", {}).get("id")
                if not template_id:
                    raise Exception(f"Failed to extract template ID from response: {json.dumps(response, indent=2)}")
                
                print(f"Created template with GraphQL, ID: {template_id}", file=sys.stderr)
                return template_id
                
            except Exception as graphql_error:
                print(f"Attempt {attempt + 1}/{retries}: Error: {graphql_error}", file=sys.stderr)
                if attempt < retries - 1:
                    print(f"Retrying in {delay} seconds...", file=sys.stderr)
                    sleep(delay)
                    continue
                raise Exception(f"Failed to create template after {retries} attempts: {graphql_error}")
    
    raise Exception(f"Could not create template for {name} with image {image_name}")

def main():
    """Deploy RunPod serverless endpoints."""
    try:
        initialize_runpod()

        # Get Docker image names from environment variables
        whisper_image = os.getenv("WHISPER_IMAGE")
        tts_image = os.getenv("TTS_IMAGE")
        llm_image = os.getenv("LLM_IMAGE")
        print(f"Docker images: WHISPER_IMAGE={whisper_image}, TTS_IMAGE={tts_image}, LLM_IMAGE={llm_image}", file=sys.stderr)
        if not all([whisper_image, tts_image, llm_image]):
            raise ValueError("Missing one or more Docker image environment variables")
            
        # Use manually provided volume ID
        volume_id = "ngb3vr286n"
        print(f"Using existing volume with ID: {volume_id}", file=sys.stderr)

        # Validate volume ID
        volumes = get_volumes()
        if not any(v["id"] == volume_id for v in volumes):
            raise ValueError(f"Volume ID {volume_id} not found. Available volumes: {[v['id'] for v in volumes]}")

        # Get endpoints
        endpoints = get_endpoints()
        endpoint_ids = {"whisper": None, "tts": None, "llm": None}
        
        print(f"Found existing endpoints: {[e.get('name') for e in endpoints]}", file=sys.stderr)
        
        for endpoint in endpoints:
            name = endpoint.get("name", "")
            if name.startswith("whisper-worker"):
                endpoint_ids["whisper"] = endpoint.get("id")
                print(f"Found whisper endpoint: {name} with ID: {endpoint.get('id')}", file=sys.stderr)
            elif name.startswith("tts-worker"):
                endpoint_ids["tts"] = endpoint.get("id")
                print(f"Found tts endpoint: {name} with ID: {endpoint.get('id')}", file=sys.stderr)
            elif name.startswith("llm-worker"):
                endpoint_ids["llm"] = endpoint.get("id")
                print(f"Found llm endpoint: {name} with ID: {endpoint.get('id')}", file=sys.stderr)

        # Define environment variables for each worker
        env_vars = {
            "whisper": {
                "MODEL_PATH": "/workspace/models",
                "CUDA_VISIBLE_DEVICES": "0"
            },
            "tts": {
                "MODEL_PATH": "/workspace/models",
                "ADDITIONAL_MODELS_DIR": "/workspace/custom-voices",
                "DEFAULT_VOICE": "lessac"
            },
            "llm": {
                "MODEL_ID": "meta-llama/Meta-Llama-3-8B-Instruct",
                "MODEL_PATH": "/workspace/models",
                "GPU_COUNT": "1",
                "GPU_MEMORY_UTILIZATION": "0.85",
                "CACHE_DIR": "/workspace/models/cache",
                "PRELOAD_MODEL": "true"
            }
        }

        # Get or create template IDs with environment variables and volume
        template_ids = {
            "whisper": create_or_update_template(
                "whisper-worker-template", 
                whisper_image, 
                env_vars=env_vars["whisper"],
                volume_id=volume_id
            ),
            "tts": create_or_update_template(
                "tts-worker-template", 
                tts_image, 
                env_vars=env_vars["tts"],
                volume_id=volume_id
            ),
            "llm": create_or_update_template(
                "llm-worker-template", 
                llm_image, 
                env_vars=env_vars["llm"],
                volume_id=volume_id
            )
        }

        # Create or update endpoints
        responses = {}
        worker_names = {
            "whisper": "whisper-worker",
            "tts": "tts-worker",
            "llm": "llm-worker"
        }
        
        for worker in ["whisper", "tts", "llm"]:
            worker_name = worker_names[worker]
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
                    gpu_type = "NVIDIA A10G"
                    if worker == "tts":
                        gpu_type = "CPU"
                    responses[worker] = runpod.create_endpoint(
                        name=worker_name,
                        template_id=template_id,
                        gpu_ids=[gpu_type],
                        workers_max=1,
                        workers_min=0,
                        idle_timeout=5,
                        flashboot=True
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