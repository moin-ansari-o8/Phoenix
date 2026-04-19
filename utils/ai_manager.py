import json
import logging
from typing import Optional, Dict


class AIDecisionMaker:
    """
    Manages AI Model resolution. Routes logic to Local (Ollama)
    or Online (Cohere/OpenAI) based on config settings.
    Provides logic modeled after IGRS's ModelManager.py but scoped for Phoenix intent decisions.
    """

    def __init__(self, config_path: str = "core/config.json"):
        self.config_path = config_path
        self.config = self._read_config()
        self.ai_settings = self.config.get("ai_manager", {})

    def _read_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {}

    def get_active_model(self) -> Dict[str, str]:
        """
        Determines the current active AI model settings.
        Returns a dict containing 'mode' (local/online) and 'model_name'.
        """
        mode = self.ai_settings.get("current_mode", "local")

        if mode == "local":
            models = self.ai_settings.get("local", {})
        else:
            models = self.ai_settings.get("online", {})

        # Find whichever model is marked True
        active_model = None
        for model_name, is_active in models.items():
            if is_active:
                active_model = model_name
                break

        return {"mode": mode, "model_name": active_model}

    def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Takes the prompt and routes it to the correct AI Handler based
        on local/online configuration.
        """
        model_info = self.get_active_model()
        mode = model_info["mode"]
        model_name = model_info["model_name"]

        if not model_name:
            return "Error: No active AI model selected in config."

        if mode == "local":
            return self._query_local(prompt, model_name, context)
        elif mode == "online":
            return self._query_online(prompt, model_name, context)
        else:
            return f"Error: Unknown AI mode '{mode}'."

    def _query_local(self, prompt: str, model_name: str, context: Optional[str]) -> str:
        # TODO: Implement Ollama local endpoint querying here
        # (similar to IGRS ollama_generate but tied to Phoenix)
        logging.info(f"Querying LOCAL Ollama Model: {model_name}")
        return f"[Simulated Local Response using {model_name}]: I understand."

    def _query_online(
        self, prompt: str, model_name: str, context: Optional[str]
    ) -> str:
        # TODO: Implement Cohere / OpenAI API querying here
        logging.info(f"Querying ONLINE Model: {model_name}")
        return f"[Simulated Online Response using {model_name}]: I understand."
