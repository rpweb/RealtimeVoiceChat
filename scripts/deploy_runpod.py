import runpod
import json
import os
import sys
import requests
from typing import Dict, Optional, List

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
        return templates
    except Exception as e:
        print(f"Error fetching templates: {e}", file=sys.stderr)
        return []

def get_or_create_network_volume(name: str = "models-volume", size_gb: int = 20) -> Optional[str]:
    """Get existing network volume or create a new one if it doesn't exist."""
    query = """
    query {
        myself {
            volumes {
                id
                name
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
        
        volumes = response.get("data", {}).get("myself", {}).get("volumes", [])
        for volume in volumes:
            if volume["name"] == name:
                print(f"Using existing volume '{name}' with ID: {volume['id']}", file=sys.stderr)
                return volume["id"]
        
        # Create new volume
        mutation = f"""
        mutation {{
            podVolumeSave(input: {{ name: "{name}", sizeGB: {size_gb} }}) {{
                id
            }}
        }}
        """
        
        response = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": mutation},
            headers={"Authorization": f"Bearer {runpod.api_key}"}
        ).json()
        
        volume_id = response.get("data", {}).get("podVolumeSave", {}).get("id")
        if volume_id:
            print(f"Created new volume '{name}' with ID: {volume_id}", file=sys.stderr)
            return volume_id
        else:
            print(f"Failed to create volume '{name}': {json.dumps(response, indent=2)}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error with network volume: {e}", file=sys.stderr)
        return None

def create_or_update_template(
    name: str, 
    image_name: str, 
    env_vars: Dict[str, str] = None,
    volume_id: str = None
) -> Optional[str]:
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
        # Prepare environment variables
        environment = {}
        if env_vars:
            environment = env_vars
            
        # Prepare volume mounts
        container_disk_in_gb = 5
        volume_mounts = []
        if volume_id:
            volume_mounts.append({
                "volumeId": volume_id,
                "mountPath": "/workspace"
            })
            
        print(f"Creating new template '{name}' with image '{image_name}'", file=sys.stderr)
        
        # Use GraphQL to create template with env vars and volume
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
                "containerDiskSizeGB": container_disk_in_gb
            }
        }
        
        # Add environment variables if provided
        if env_vars:
            env_list = []
            for key, value in env_vars.items():
                env_list.append({"key": key, "value": value})
            variables["input"]["env"] = env_list
            
        # Add volume mounts if provided
        if volume_id:
            variables["input"]["volumeMounts"] = [{"volumeId": volume_id, "mountPath": "/workspace"}]
            
        response = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": mutation, "variables": variables},
            headers={"Authorization": f"Bearer {runpod.api_key}"}
        ).json()
        
        if "errors" in response:
            error_msg = response.get("errors", [{}])[0].get("message", "Unknown error")
            print(f"Error creating template '{name}': {error_msg}", file=sys.stderr)
            if "Template name must be unique" in error_msg:
                raise ValueError(f"Template '{name}' exists with invalid imageName. Update it in RunPod console.")
            raise Exception(error_msg)
            
        template_id = response.get("data", {}).get("podTemplateSave", {}).get("id")
        if not template_id:
            raise Exception(f"Failed to create template: {json.dumps(response, indent=2)}")
            
        print(f"Created template '{name}' with ID: {template_id}", file=sys.stderr)
        return template_id
    except Exception as e:
        print(f"Error creating template '{name}': {str(e)}", file=sys.stderr)
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
            
        # Get or create network volume for model storage - make it optional
        volume_id = None
        try:
            volume_id = get_or_create_network_volume(name="models-volume", size_gb=40)
        except Exception as e:
            print(f"Warning: Could not create network volume: {e}. Continuing without volume.", file=sys.stderr)

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

        # Define environment variables for each worker
        env_vars = {
            "whisper": {
                "MODEL_PATH": "/workspace/models" if volume_id else "./models",
                "CUDA_VISIBLE_DEVICES": "0"
            },
            "tts": {
                "MODEL_PATH": "/workspace/models" if volume_id else "./models",
                "ADDITIONAL_MODELS_DIR": "/workspace/custom-voices" if volume_id else "./custom-voices",
                "DEFAULT_VOICE": "lessac"
            },
            "llm": {
                "MODEL_ID": "meta-llama/Meta-Llama-3-8B-Instruct",
                "MODEL_PATH": "/workspace/models" if volume_id else "./models",
                "GPU_COUNT": "1",
                "GPU_MEMORY_UTILIZATION": "0.85",
                "CACHE_DIR": "/workspace/models/cache" if volume_id else "./models/cache",
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
                    gpu_type = "NVIDIA A10G"  # or "NVIDIA A100" for even better performance
                    if worker == "tts":
                        # TTS can run on CPU
                        gpu_type = "CPU" 
                    responses[worker] = runpod.create_endpoint(
                        name=worker_name,
                        template_id=template_id,
                        gpu_ids=[gpu_type],
                        workers_max=1,      # Only 1 worker for testing purposes
                        workers_min=0,      # No always-on workers (saves money but adds cold start)
                        idle_timeout=5,     # Scale down after 5 seconds of inactivity (more cost effective)
                        flashboot=True      # Enable flashboot for faster cold starts (2-3x quicker)
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