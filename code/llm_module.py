# llm_module.py
import re
import logging
import os
import sys
import time
import json
import uuid
from typing import Generator, List, Dict, Optional, Any
from threading import Lock

# --- Library Dependencies ---
try:
    from openai import OpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    class APIError(Exception): pass
    class APITimeoutError(APIError): pass
    class RateLimitError(APIError): pass
    class APIConnectionError(APIError): pass
    logging.warning("🤖⚠️ openai library not installed. OpenAI backend will not function.")

# Configure logging
# Use the root logger configured by the main application if available, else basic config
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
# Check if root logger already has handlers (likely configured by main app)
if not logging.getLogger().handlers:
    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout) # Default to stdout if not configured
logger = logging.getLogger(__name__) # Get logger for this module
logger.setLevel(log_level) # Ensure module logger respects level

# --- Environment Variable Configuration ---
try:
    import importlib.util
    dotenv_spec = importlib.util.find_spec("dotenv")
    if dotenv_spec:
        from dotenv import load_dotenv
        load_dotenv()
        logger.debug("🤖⚙️ Loaded environment variables from .env file.")
    else:
        logger.debug("🤖⚙️ python-dotenv not installed, skipping .env load.")
except ImportError:
    logger.debug("🤖💥 Error importing dotenv, skipping .env load.")

OPENAI_API_KEY = os.getenv("RUNPOD_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.runpod.ai/v2/flucjdcomu60vx/openai/v1")

# --- Backend Client Creation Functions ---
def _create_openai_client(api_key: Optional[str], base_url: Optional[str] = None) -> OpenAI:
    """
    Creates and configures an OpenAI API client instance.

    Handles API key logic and optional base URL configuration. 
    Sets default timeout and retries.

    Args:
        api_key: The OpenAI API key.
        base_url: The base URL for the API endpoint (e.g., for custom deployments).

    Returns:
        An initialized OpenAI client instance.

    Raises:
        ImportError: If the 'openai' library is not installed.
        Exception: If client initialization fails for other reasons.
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("openai library is required for this backend but not installed.")
    try:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        client_args = {
            "api_key": api_key,
            "timeout": 30.0,
            "max_retries": 2
        }
        if base_url:
            client_args["base_url"] = base_url

        client = OpenAI(**client_args)
        logger.info(f"🤖🔌 Prepared OpenAI client (Base URL: {base_url or 'Default'}).")
        return client
    except Exception as e:
        logger.error(f"🤖💥 Failed to initialize OpenAI client: {e}")
        raise

# --- LLM Class ---
class LLM:
    """
    Provides a unified interface for interacting with OpenAI LLM backend.

    Handles client initialization, streaming generation, request cancellation,
    and system prompts.
    """
    SUPPORTED_BACKENDS = ["openai"]

    def __init__(
        self,
        backend: str,
        model: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        no_think: bool = False,
    ):
        """
        Initializes the LLM interface for OpenAI backend.

        Args:
            backend: The name of the LLM backend to use (must be "openai").
            model: The identifier for the specific model to use.
            system_prompt: An optional system prompt to prepend to conversations.
            api_key: API key for OpenAI backend.
            base_url: Optional base URL for the backend API (overrides defaults/env vars).
            no_think: Experimental flag (currently unused in core logic, intended for future prompt modification).

        Raises:
            ValueError: If an unsupported backend is specified.
            ImportError: If required libraries for the OpenAI backend are not installed.
        """
        logger.info(f"🤖⚙️ Initializing LLM with backend: {backend}, model: {model}, system_prompt: {system_prompt}")
        self.backend = backend.lower()
        if self.backend not in self.SUPPORTED_BACKENDS:
            raise ValueError(f"Unsupported backend '{backend}'. Supported: {self.SUPPORTED_BACKENDS}")

        if not OPENAI_AVAILABLE:
             raise ImportError("openai library is required for the 'openai' backend but not installed.")

        self.model = model
        self.system_prompt = system_prompt
        self._api_key = api_key
        self._base_url = base_url
        self.no_think = no_think # Not used yet, but kept for future use

        self.client: Optional[OpenAI] = None
        self._client_initialized: bool = False
        self._client_init_lock = Lock()
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        self._requests_lock = Lock()

        logger.info(f"🤖⚙️ Configuring LLM instance: backend='{self.backend}', model='{self.model}'")

        self.effective_openai_key = self._api_key or OPENAI_API_KEY
        self.effective_openai_base_url = self._base_url or OPENAI_BASE_URL

        self.system_prompt_message = None
        if self.system_prompt:
            self.system_prompt_message = {"role": "system", "content": self.system_prompt}
            logger.info(f"🤖💬 System prompt set.")

    def _lazy_initialize_clients(self) -> bool:
        """
        Initializes OpenAI client on first use (thread-safe).

        Creates the OpenAI SDK client instance for communication with the API.

        Returns:
            True if the client is initialized and ready, False otherwise.
        """
        if self._client_initialized:
            return self.client is not None

        with self._client_init_lock:
            if self._client_initialized: # Double check
                return self.client is not None

            logger.debug(f"🤖🔄 Lazy initializing client for backend: {self.backend}")
            init_ok = False

            try:
                self.client = _create_openai_client(self.effective_openai_key, base_url=self.effective_openai_base_url)
                init_ok = self.client is not None

                if init_ok:
                    logger.info(f"🤖✅ Client initialized successfully for backend: {self.backend}.")
                else:
                    logger.error(f"🤖💥 Initialization failed for backend: {self.backend}.")
            except Exception as e:
                logger.exception(f"🤖💥 Critical failure during lazy initialization for {self.backend}: {e}")
                init_ok = False
            finally:
                # Mark as initialized regardless of success/failure
                self._client_initialized = True

            return init_ok

    def cancel_generation(self, request_id: Optional[str] = None) -> bool:
        """
        Requests cancellation of active generation streams.

        If `request_id` is provided, cancels that specific stream.
        If `request_id` is None, attempts to cancel all currently active streams.
        Cancellation involves removing the request from tracking and attempting to
        close the underlying network stream/response object.

        Args:
            request_id: The unique ID of the generation request to cancel, or None to cancel all.

        Returns:
            True if at least one request cancellation was attempted, False otherwise.
        """
        cancelled_any = False
        with self._requests_lock:
            ids_to_cancel = []
            if request_id is None:
                if not self._active_requests:
                    logger.debug("🤖🗑️ Cancel all requested, but no active requests found.")
                    return False
                logger.info(f"🤖🗑️ Attempting to cancel ALL active generation requests ({len(self._active_requests)}).")
                ids_to_cancel = list(self._active_requests.keys())
            else:
                if request_id not in self._active_requests:
                    logger.warning(f"🤖🗑️ Cancel requested for ID '{request_id}', but it's not an active request.")
                    return False
                logger.info(f"🤖🗑️ Attempting to cancel generation request: {request_id}")
                ids_to_cancel.append(request_id)

            # Perform the cancellation
            for req_id in ids_to_cancel:
                # Call the internal cancellation method which now tries to close the stream
                if self._cancel_single_request_unsafe(req_id):
                    cancelled_any = True
        return cancelled_any

    def _cancel_single_request_unsafe(self, request_id: str) -> bool:
        """
        Internal helper to handle cancellation for a single request (thread-unsafe).

        Removes the request data from the `_active_requests` dictionary and attempts
        to call the `close()` method on the associated stream/response object, if available.
        Must be called while holding `_requests_lock`.

        Args:
            request_id: The unique ID of the request to cancel.

        Returns:
            True if the request was found and removal/close attempt was made, False otherwise.
        """
        request_data = self._active_requests.pop(request_id, None)
        if not request_data:
            # This might happen if it finished or was cancelled concurrently
            logger.debug(f"🤖🗑️ Request {request_id} already removed before cancellation attempt.")
            return False

        request_type = request_data.get("type", "unknown")
        stream_obj = request_data.get("stream")
        logger.debug(f"🤖🗑️ Cancelling request {request_id} (type: {request_type}). Stream object: {type(stream_obj)}")

        # --- Attempt to close the underlying stream/response ---
        if stream_obj:
            try:
                # Check if it has a close method and call it
                if hasattr(stream_obj, 'close') and callable(stream_obj.close):
                    logger.debug(f"🤖🗑️ [{request_id}] Attempting to close stream/response object...")
                    stream_obj.close()
                    logger.info(f"🤖🗑️ Closed stream/response for cancelled request {request_id}.")
                else:
                    logger.warning(f"🤖⚠️ [{request_id}] Stream object of type {type(stream_obj)} does not have a callable 'close' method. Cannot explicitly close.")
            except Exception as e:
                # Log error during close but continue - the request is still removed from tracking
                logger.error(f"🤖💥 Error closing stream/response for request {request_id}: {e}", exc_info=False)
        else:
             logger.warning(f"🤖⚠️ [{request_id}] No stream object found in request data to close.")

        # Log the removal from tracking
        logger.info(f"🤖🗑️ Removed generation request {request_id} from tracking (close attempted).")
        return True # Indicate removal occurred

    def _register_request(self, request_id: str, request_type: str, stream_obj: Optional[Any]):
        """
        Registers an active generation stream for cancellation tracking (thread-safe).

        Stores the request ID, type, stream object, and start time internally.

        Args:
            request_id: The unique ID for the generation request.
            request_type: The backend type (e.g., "openai").
            stream_obj: The underlying stream/response object associated with the request.
        """
        with self._requests_lock:
            if request_id in self._active_requests:
                logger.warning(f"🤖⚠️ Request ID {request_id} already registered. Overwriting.")
            self._active_requests[request_id] = {
                "type": request_type,
                "stream": stream_obj,
                "start_time": time.time()
            }
            logger.debug(f"🤖ℹ️ Registered active request: {request_id} (Type: {request_type}, Stream: {type(stream_obj)}, Count: {len(self._active_requests)})")

    def cleanup_stale_requests(self, timeout_seconds: int = 300):
        """
        Finds and attempts to cancel requests older than the specified timeout.

        Iterates through active requests and calls `cancel_generation` for any
        request whose start time exceeds the timeout duration.

        Args:
            timeout_seconds: The maximum age in seconds before a request is considered stale.

        Returns:
            The number of stale requests for which cancellation was attempted.
        """
        stale_ids = []
        now = time.time()
        # Find stale IDs without holding lock for too long
        with self._requests_lock:
            stale_ids = [
                req_id for req_id, req_data in self._active_requests.items()
                if (now - req_data.get("start_time", 0)) > timeout_seconds
            ]

        if stale_ids:
            logger.info(f"🤖🧹 Found {len(stale_ids)} potentially stale requests (>{timeout_seconds}s). Cleaning up...")
            cleaned_count = 0
            for req_id in stale_ids:
                # cancel_generation handles locking internally and now attempts to close stream
                if self.cancel_generation(req_id):
                    cleaned_count += 1
            logger.info(f"🤖🧹 Cleaned up {cleaned_count}/{len(stale_ids)} stale requests (attempted stream close).")
            return cleaned_count
        return 0

    def prewarm(self, max_retries: int = 1) -> bool:
        """
        Attempts to "prewarm" the LLM connection and potentially load the model.

        Runs a simple, short generation task ("Respond with only the word 'OK'.")
        to trigger lazy initialization (including potential `ollama ps` check)
        and ensure the backend is responsive before actual use. Includes basic retry logic.

        Args:
            max_retries: The number of times to retry the generation task if a
                         connection/timeout error occurs (0 means one attempt total).

        Returns:
            True if the prewarm generation completed successfully (even with no content),
            False if initialization or generation failed after retries.
        """
        prompt = "Respond with only the word 'OK'."
        logger.info(f"🤖🔥 Attempting prewarm for '{self.model}' on backend '{self.backend}'...")

        # Lazy initialization now includes the 'ollama ps' logic if needed
        if not self._lazy_initialize_clients():
            logger.error("🤖🔥💥 Prewarm failed: Could not initialize backend client/connection.")
            return False

        attempts = 0
        last_error = None
        while attempts <= max_retries:
            prewarm_start_time = time.time()
            prewarm_request_id = f"prewarm-{self.backend}-{uuid.uuid4()}"
            generator = None
            full_response = ""
            token_count = 0
            first_token_time = None

            try:
                logger.info(f"🤖🔥 Prewarm Attempt {attempts + 1}/{max_retries+1} calling generate (ID: {prewarm_request_id})...")
                generator = self.generate(
                    text=prompt,
                    history=None,
                    use_system_prompt=True,
                    request_id=prewarm_request_id,
                    temperature=0.1
                )

                gen_start_time = time.time()
                # Consume the generator fully
                for token in generator:
                    if first_token_time is None:
                        first_token_time = time.time()
                        logger.info(f"🤖🔥⏱️ Prewarm TTFT: {(first_token_time - gen_start_time):.4f}s")
                    full_response += token
                    token_count += 1
                # End of loop means generator is exhausted
                gen_end_time = time.time()
                logger.info(f"🤖🔥ℹ️ Prewarm consumed {token_count} tokens in {(gen_end_time - gen_start_time):.4f}s. Full response: '{full_response}'")

                if token_count == 0 and not full_response:
                     logger.warning(f"🤖🔥⚠️ Prewarm yielded no response content, but generation finished.")
                # else: pass # If we got content, great.

                prewarm_end_time = time.time()
                logger.info(f"🤖🔥✅ Prewarm successful (generation finished naturally). Total time: {(prewarm_end_time - prewarm_start_time):.4f}s.")
                return True

            except (APIConnectionError, ConnectionError, TimeoutError, APITimeoutError) as e:
                last_error = e
                logger.warning(f"🤖🔥⚠️ Prewarm attempt {attempts + 1}/{max_retries+1} connection/timeout error during generation: {e}")
                if attempts < max_retries:
                    attempts += 1
                    wait_time = 2 * attempts
                    logger.info(f"🤖🔥🔄 Retrying prewarm generation in {wait_time}s...")
                    time.sleep(wait_time)
                    # Force re-check on next attempt via lazy_init in generate()
                    # Crucially, setting this False forces _lazy_initialize_clients to run again
                    # which will re-attempt the connection check AND the `ollama ps` fallback if needed.
                    self._client_initialized = False
                    logger.debug("🤖🔥🔄 Resetting client initialized flag to force re-check on retry.")
                    continue
                else:
                    logger.error(f"🤖🔥💥 Prewarm failed permanently after {attempts + 1} generation attempts due to connection issues.")
                    return False
            except (APIError, RateLimitError, RuntimeError) as e:
                last_error = e
                logger.error(f"🤖🔥💥 Prewarm attempt {attempts + 1}/{max_retries+1} API/Runtime error: {e}")
                if isinstance(e, RuntimeError) and "client failed" in str(e):
                    logger.error("   (This might indicate the initial lazy initialization failed)")
                return False # Non-connection errors are usually fatal for prewarm
            except Exception as e:
                last_error = e
                logger.exception(f"🤖🔥💥 Prewarm attempt {attempts + 1}/{max_retries+1} unexpected error.")
                return False
            finally:
                # Generate's finally block handles tracking cleanup.
                # Explicitly try closing generator here in case of error mid-stream.
                logger.debug(f"🤖🔥ℹ️ [{prewarm_request_id}] Prewarm attempt finished. generate()'s finally handles tracking cleanup.")
                if generator is not None and hasattr(generator, 'close'):
                    try:
                        generator.close()
                    except Exception as close_err:
                         logger.warning(f"🤖🔥⚠️ [{prewarm_request_id}] Error closing generator in prewarm finally: {close_err}", exc_info=False)
                generator = None # Clear local ref

            if attempts >= max_retries:
                break # Exit loop if max_retries reached without success

        logger.error(f"🤖🔥💥 Prewarm failed after exhausting retries. Last error: {last_error}")
        return False

    def generate(
        self,
        text: str,
        history: Optional[List[Dict[str, str]]] = None,
        use_system_prompt: bool = True,
        request_id: Optional[str] = None,
        **kwargs: Any
    ) -> Generator[str, None, None]:
        """
        Generates text using the configured backend, yielding tokens as a stream.

        Handles lazy initialization, message formatting, backend-specific API calls, 
        stream registration, token yielding, and resource cleanup.

        Args:
            text: The user's input prompt/text.
            history: An optional list of previous messages (dicts with "role" and "content").
            use_system_prompt: If True, prepends the configured system prompt (if any).
            request_id: An optional unique ID for this generation request. If None, one is generated.
            **kwargs: Additional backend-specific keyword arguments (e.g., temperature, top_p, stop sequences).

        Yields:
            str: Individual tokens (or small chunks of text) as they are generated by the LLM.

        Raises:
            RuntimeError: If the backend client fails to initialize.
            ConnectionError: If communication with the backend fails (initial connection or during streaming).
            ValueError: If configuration is invalid.
            APIError: For backend-specific API errors (OpenAI).
            RateLimitError: For backend-specific rate limit errors (OpenAI).
            Exception: For other unexpected errors during the generation process.
        """
        # Lazy initialization
        if not self._lazy_initialize_clients():
            # Provide a clearer error if initialization failed
            raise RuntimeError(f"LLM backend '{self.backend}' client failed to initialize.")

        req_id = request_id if request_id else f"{self.backend}-{uuid.uuid4()}"
        logger.info(f"🤖💬 Starting generation (Request ID: {req_id})")

        messages = []
        if use_system_prompt and self.system_prompt_message:
            messages.append(self.system_prompt_message)
        if history:
            messages.extend(history)

        if len(messages) == 0 or messages[-1]["role"] != "user":
            added_text = text # for normal text
            if self.no_think:
                 # This modification logic remains specific for now
                added_text = f"{text}/nothink" # for qwen 3
            logger.info(f"🧠💬 llm_module.py generate adding role user to messages, content: {added_text}")
            messages.append({"role": "user", "content": added_text})
        logger.debug(f"🤖💬 [{req_id}] Prepared messages count: {len(messages)}")

        stream_iterator = None
        stream_object_to_register = None # This is the object we need to close on cancel

        try:
            if self.backend == "openai":
                if self.client is None:
                    raise RuntimeError("OpenAI client not initialized (should have been caught by lazy_init).")
                payload = { "model": self.model, "messages": messages, "stream": True, **kwargs }
                logger.info(f"🤖💬 [{req_id}] Sending OpenAI request with payload:")
                logger.info(f"{json.dumps(payload, indent=2)}")
                stream_iterator = self.client.chat.completions.create(
                    model=self.model, messages=messages, stream=True, **kwargs
                )
                stream_object_to_register = stream_iterator # The Stream object itself
                self._register_request(req_id, "openai", stream_object_to_register)
                yield from self._yield_openai_chunks(stream_iterator, req_id)

            else:
                # This case should technically be caught by __init__
                raise ValueError(f"Backend '{self.backend}' generation logic not implemented.")

            logger.info(f"🤖✅ Finished generating stream successfully (request_id: {req_id})")

        # Catch specific exceptions first
        except (ConnectionError, APITimeoutError) as e:
             logger.error(f"🤖💥 Connection/Timeout Error during generation for {req_id}: {e}", exc_info=False)
             # Reraise as a standard ConnectionError for consistency
             raise ConnectionError(f"Communication error during generation: {e}") from e
        except (APIError, RateLimitError) as e:
             logger.error(f"🤖💥 API/Request Error during generation for {req_id}: {e}", exc_info=False)
             # Reraise the original error
             raise
        except Exception as e:
            logger.error(f"🤖💥 Unexpected error in generation pipeline for {req_id}: {e}", exc_info=True) # Log traceback for unexpected
            raise # Reraise the original exception
        finally:
            # Removes request ID from tracking AND attempts to close the stream via _cancel_single_request_unsafe
            logger.debug(f"🤖ℹ️ [{req_id}] Entering finally block for generate.")
            with self._requests_lock:
                if req_id in self._active_requests:
                    # Only log removal if it was actually present
                    logger.debug(f"🤖🗑️ [{req_id}] Removing request from tracking and attempting stream close in generate's finally block.")
                    # Perform the removal and close attempt using the existing unsafe helper
                    self._cancel_single_request_unsafe(req_id)
                else:
                    # This can happen if cancellation occurred before finally
                    logger.debug(f"🤖🗑️ [{req_id}] Request already removed from tracking before finally block completion.")
            logger.debug(f"🤖ℹ️ [{req_id}] Exiting finally block. Active requests: {len(self._active_requests)}")


    # --- Backend-Specific Chunk Yielding Helpers ---
    def _yield_openai_chunks(self, stream, request_id: str) -> Generator[str, None, None]:
        """
        Iterates over an OpenAI/LMStudio stream, yielding content chunks.

        Handles extracting content from stream chunks and checks for cancellation
        before processing each chunk. Ensures the stream is closed upon completion,
        error, or cancellation.

        Args:
            stream: The stream object returned by the OpenAI client's `create` method.
            request_id: The unique ID associated with this generation stream.

        Yields:
            str: Content chunks from the stream's delta messages.

        Raises:
            ConnectionError: If a connection error occurs during streaming, unless likely due to cancellation.
            APIError: If an API error occurs during streaming.
            Exception: For other unexpected errors during streaming.
        """
        token_count = 0
        try:
            for chunk in stream:
                # Check for cancellation *before* processing chunk
                with self._requests_lock:
                    if request_id not in self._active_requests:
                        logger.info(f"🤖🗑️ OpenAI/LMStudio stream {request_id} cancelled or finished externally during iteration.")
                        # No need to manually close stream here; cancellation logic or finally block handles it.
                        break # Exit the loop cleanly
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = delta.content
                    if content:
                        token_count += 1
                        yield content
            logger.debug(f"🤖✅ [{request_id}] Finished yielding {token_count} OpenAI tokens.")
        except APIConnectionError as e:
             # Often happens if the stream is closed prematurely by cancellation
             is_cancelled = False
             with self._requests_lock:
                 is_cancelled = request_id not in self._active_requests
             if is_cancelled:
                  logger.warning(f"🤖⚠️ OpenAI stream connection error likely due to cancellation for {request_id}: {e}")
             else:
                  logger.error(f"🤖💥 OpenAI API connection error during streaming ({request_id}): {e}")
                  raise ConnectionError(f"OpenAI communication error during streaming: {e}") from e
        except APIError as e:
            logger.error(f"🤖💥 OpenAI API error during streaming ({request_id}): {e}")
            raise # Reraise for generate() to handle
        except Exception as e:
            # Catch other potential errors during iteration
            is_cancelled = False
            with self._requests_lock:
                is_cancelled = request_id not in self._active_requests
            if is_cancelled:
                logger.warning(f"🤖⚠️ OpenAI stream error likely due to cancellation for {request_id}: {e}")
            else:
                logger.error(f"🤖💥 Unexpected error during OpenAI streaming ({request_id}): {e}", exc_info=True)
                raise # Reraise for generate() to handle
        finally:
            # Ensure the stream is closed if iteration finishes or breaks
            # The cancellation logic also tries to close, but this catches normal completion
            if stream and hasattr(stream, 'close') and callable(stream.close):
                 try:
                     logger.debug(f"🤖🗑️ [{request_id}] Closing OpenAI stream in _yield_openai_chunks finally.")
                     stream.close()
                 except Exception as close_err:
                     logger.warning(f"🤖⚠️ [{request_id}] Error closing OpenAI stream in finally: {close_err}", exc_info=False)

    def measure_inference_time(
        self,
        num_tokens: int = 10,
        **kwargs: Any
    ) -> Optional[float]:
        """
        Measures the time taken to generate a target number of initial tokens.

        Uses a fixed, predefined prompt designed to elicit a somewhat predictable
        response length. Times the generation process from the moment the generator
        is obtained until the target number of tokens is yielded or generation ends.
        Ensures the backend client is initialized first.

        Args:
            num_tokens: The target number of tokens to generate before stopping measurement.
            **kwargs: Additional keyword arguments passed to the `generate` method
                      (e.g., temperature=0.1).

        Returns:
            The time taken in milliseconds to generate the actual number of tokens
            produced (up to `num_tokens`), or None if generation failed, produced 0 tokens,
            or encountered an error during initialization or generation.
        """
        if num_tokens <= 0:
            logger.warning("🤖⏱️ Cannot measure inference time for 0 or negative tokens.")
            return None

        # Ensure client is ready
        if not self._lazy_initialize_clients():
            logger.error(f"🤖⏱️💥 Measurement failed: Could not initialize backend client for {self.backend}.")
            return None

        # --- Define specific prompts for measurement ---
        measurement_system_prompt = "You are a precise assistant. Follow instructions exactly."
        # This text is designed to likely produce > 10 tokens across different tokenizers.
        measurement_user_prompt = "Repeat the following sequence exactly, word for word: one two three four five six seven eight nine ten eleven twelve"
        measurement_history = [
            {"role": "system", "content": measurement_system_prompt},
            {"role": "user", "content": measurement_user_prompt}
        ]
        # ---------------------------------------------

        req_id = f"measure-{self.backend}-{uuid.uuid4()}"
        logger.info(f"🤖⏱️ Measuring inference time for {num_tokens} tokens (Request ID: {req_id}). Using fixed measurement prompt.")
        logger.debug(f"🤖⏱️ [{req_id}] Measurement history: {measurement_history}")

        token_count = 0
        start_time = None
        end_time = None
        generator = None
        actual_tokens_generated = 0

        try:
            # Pass the constructed history and ensure use_system_prompt is False
            # The 'text' argument to generate is ignored when history is provided containing the user message.
            generator = self.generate(
                text="", # Text is ignored as history provides the user message
                history=measurement_history,
                use_system_prompt=False, # Explicitly disable default system prompt
                request_id=req_id,
                **kwargs # Pass any extra args like temperature
            )

            # Iterate and time
            start_time = time.time() # Start timing *after* generate() call returns generator
            for token in generator:
                if token_count == 0:
                     # Could capture TTFT here if needed: time.time() - start_time
                     pass
                token_count += 1
                # logger.debug(f"[{req_id}] Token {token_count}: '{token}'") # Optional: very verbose
                if token_count >= num_tokens:
                    end_time = time.time()
                    logger.debug(f"🤖⏱️ [{req_id}] Reached target {num_tokens} tokens.")
                    break # Stop iterating

            # If loop finished without breaking, record end time here
            if end_time is None:
                end_time = time.time()
                logger.debug(f"🤖⏱️ [{req_id}] Generation finished naturally after {token_count} tokens (may be less than requested {num_tokens}).")

            actual_tokens_generated = token_count

        except (ConnectionError, APIError, RuntimeError, Exception) as e:
            logger.error(f"🤖⏱️💥 Error during inference time measurement ({req_id}): {e}", exc_info=False)
            # Let finally block handle potential generator cleanup
            return None # Indicate failure
        finally:
            # Ensure generator resources are released if the loop was broken early
            # The generate() method's finally block handles request tracking removal AND attempts close.
            # We still explicitly try closing the generator here as a fallback.
            if generator and hasattr(generator, 'close'):
                try:
                    logger.debug(f"🤖⏱️🗑️ [{req_id}] Closing generator in measure_inference_time finally.")
                    generator.close()
                except Exception as close_err:
                    # Log but don't prevent returning time if measured
                    logger.warning(f"🤖⏱️⚠️ [{req_id}] Error closing generator in finally: {close_err}", exc_info=False)
            generator = None # Clear reference


        # --- Calculate and Return Result ---
        if start_time is None or end_time is None:
             logger.error(f"🤖⏱️💥 [{req_id}] Measurement failed: Start or end time not recorded.")
             return None

        if actual_tokens_generated == 0:
             logger.warning(f"🤖⏱️⚠️ [{req_id}] Measurement invalid: 0 tokens were generated.")
             return None

        duration_sec = end_time - start_time
        duration_ms = duration_sec * 1000

        logger.info(
            f"🤖⏱️✅ Measured ~{duration_ms:.2f} ms for {actual_tokens_generated} tokens "
            f"(target: {num_tokens}) for model '{self.model}' on backend '{self.backend}' using fixed prompt. (Request ID: {req_id})"
        )

        # Return the time taken for the actual tokens generated.
        return duration_ms


# --- Context Manager ---
class LLMGenerationContext:
    """
    A context manager for safely handling LLM generation streams.

    Ensures that the underlying generation stream is properly requested for cancellation
    (including attempting to close the network connection) when the context is exited,
    whether normally or due to an exception.
    """
    def __init__(
        self,
        llm: LLM,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        use_system_prompt: bool = True,
        **kwargs: Any
        ):
        """
        Initializes the generation context.

        Args:
            llm: The LLM instance to use for generation.
            prompt: The user's input prompt/text.
            history: Optional list of previous messages.
            use_system_prompt: If True, uses the LLM's configured system prompt.
            **kwargs: Additional arguments to pass to the `llm.generate` method.
        """
        self.llm = llm
        self.prompt = prompt
        self.history = history
        self.use_system_prompt = use_system_prompt
        self.kwargs = kwargs
        self.generator: Optional[Generator[str, None, None]] = None
        self.request_id: str = f"ctx-{llm.backend}-{uuid.uuid4()}"
        self._entered: bool = False

    def __enter__(self) -> Generator[str, None, None]:
        """
        Enters the context, starts generation, and returns the token generator.

        Calls the LLM's `generate` method and registers the request.

        Returns:
            A generator yielding tokens from the LLM.

        Raises:
            RuntimeError: If the context is re-entered or generator creation fails.
            (Propagates exceptions from `llm.generate`).
        """
        if self._entered:
            raise RuntimeError("LLMGenerationContext cannot be re-entered")
        self._entered = True
        logger.debug(f"🤖▶️ [{self.request_id}] Entering LLMGenerationContext.")
        try:
            # Generate call now implicitly runs lazy_init
            self.generator = self.llm.generate(
                self.prompt,
                self.history,
                self.use_system_prompt,
                request_id=self.request_id,
                **self.kwargs
            )
            return self.generator
        except Exception as e:
            logger.error(f"🤖💥 [{self.request_id}] Failed generator creation in context: {e}", exc_info=True)
            # Attempt to clean up if registration happened before error (tries close)
            self.llm.cancel_generation(self.request_id)
            self._entered = False
            raise # Reraise the exception

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the context, ensuring the generation stream is cancelled and closed.

        Calls `llm.cancel_generation` to remove tracking and attempt stream closure.
        Also explicitly attempts to close the generator object itself as a safeguard.

        Args:
            exc_type: The type of exception that caused the context to be exited (if any).
            exc_val: The exception instance (if any).
            exc_tb: The traceback (if any).

        Returns:
            False, indicating that exceptions (if any) should not be suppressed.
        """
        logger.debug(f"🤖◀️ [{self.request_id}] Exiting LLMGenerationContext (Exc: {exc_type}).")
        # Calls the modified cancel_generation, which now attempts to close the stream
        self.llm.cancel_generation(self.request_id) # Removes tracking & attempts close

        # Explicit close attempt in __exit__ is now less critical as cancel_generation
        # and the _yield_* helpers' finally blocks also attempt closure.
        # Keep it as a final safeguard.
        if self.generator and hasattr(self.generator, 'close'):
            try:
                logger.debug(f"🤖🗑️ [{self.request_id}] Explicitly closing generator in context exit (final check).")
                self.generator.close()
            except Exception as e:
                 logger.warning(f"🤖⚠️ [{self.request_id}] Error closing generator in context exit: {e}")

        self.generator = None
        self._entered = False
        # If an exception occurred, don't suppress it
        return False



# --- Example Usage ---
if __name__ == "__main__":
    # Setup logging for the example itself
    # Use basicConfig here as it's the main script
    main_log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    main_log_level = getattr(logging, main_log_level_str, logging.INFO)
    logging.basicConfig(level=main_log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout)
    main_logger = logging.getLogger(__name__) # Logger for this __main__ block
    main_logger.info("🤖🚀 --- Running LLM Module Example ---")

    # --- OpenAI Example ---
    if OPENAI_AVAILABLE:
        try:
            main_logger.info(f"\n🤖⚙️ --- Initializing OpenAI ---")
            openai_llm = LLM(
                backend="openai",
                model="Qwen/Qwen2.5-7B-Instruct-AWQ",  # Use a smaller model for testing
                system_prompt="You are concise and helpful."
            )

            # Prewarm will trigger lazy init
            main_logger.info("🤖🔥 --- Running OpenAI Prewarm ---")
            prewarm_success = openai_llm.prewarm(max_retries=0) # Only one attempt for prewarm after init

            if prewarm_success:
                 main_logger.info("🤖✅ OpenAI Prewarm/Initialization OK.")

                 # --- Run Measurement ---
                 main_logger.info("🤖⏱️ --- Running OpenAI Inference Time Measurement ---")
                 inf_time = openai_llm.measure_inference_time(num_tokens=10, temperature=0.1)
                 if inf_time is not None:
                     main_logger.info(f"🤖⏱️ --- Measured Inference Time: {inf_time:.2f} ms ---")
                 else:
                     main_logger.warning("🤖⏱️⚠️ --- Inference Time Measurement Failed ---")

                 # --- Run Generation ---
                 main_logger.info("🤖▶️ --- Running OpenAI Generation via Context (Post-Prewarm) ---")
                 try:
                     # Use the context manager
                     with LLMGenerationContext(openai_llm, "What is the capital of France? Respond briefly.") as generator:
                         print("\nOpenAI Response: ", end="", flush=True)
                         response_text = ""
                         for token in generator:
                             print(token, end="", flush=True)
                             response_text += token
                         print("\n") # Newline after response
                     main_logger.info("🤖✅ OpenAI generation complete.")

                     # Example of direct generate call (after context)
                     main_logger.info("🤖💬 --- Running OpenAI Generation via direct call ---")
                     direct_gen = openai_llm.generate("List three large cities in Germany.")
                     print("\nOpenAI Direct Response: ", end="", flush=True)
                     for token in direct_gen:
                          print(token, end="", flush=True)
                     print("\n")
                     main_logger.info("🤖✅ OpenAI direct generation complete.")

                 except (ConnectionError, RuntimeError, Exception) as e:
                     # Catch specific ConnectionError raised on init/gen failure
                     if isinstance(e, ConnectionError):
                          main_logger.error(f"🤖💥 OpenAI Connection Error during Generation: {e}")
                          main_logger.error("   🤖🔌 Please ensure the OpenAI API key is valid and the service is accessible.")
                     else:
                          main_logger.error(f"🤖💥 OpenAI Generation Runtime/Other Error: {e}", exc_info=True)

            else:
                 main_logger.error("🤖❌ OpenAI Prewarm/Initialization Failed. Could not connect or encountered error. Skipping measurement and generation tests.")

        except (ImportError, ValueError, Exception) as e:
             main_logger.error(f"🤖💥 Failed to initialize or run OpenAI: {e}", exc_info=True)
    else:
        main_logger.warning("🤖⚠️ Skipping OpenAI tests: 'openai' library not installed.")

    main_logger.info("\n" + "="*40)
    main_logger.info("🤖🏁 --- LLM Module Example Script Finished ---")