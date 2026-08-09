"""
OllamaHelperPHNX.py - Ollama LLM Integration for Natural Language Processing
Handles intent extraction, data parsing, and natural response generation
"""

import os
import json
import requests
from datetime import datetime


class OllamaHelper:
    """Interface with Ollama for natural language understanding"""

    def __init__(
        self, model="mistral:7b-instruct", ollama_url="http://localhost:11434"
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        self._server_ready = False

    def _wait_for_ready(self, max_wait=90):
        """Poll /api/tags until Ollama server is alive (up to max_wait seconds)."""
        import time
        for _ in range(max_wait):
            try:
                r = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                if r.status_code == 200:
                    self._server_ready = True
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def chat(self, messages, tools=None, timeout=120, temperature=0.4,
             num_predict=None):
        """POST /api/chat. Returns the raw `message` dict, or {'error': ...}.

        The returned dict may contain 'content' (str) and/or 'tool_calls' (list).
        keep_alive holds the model in RAM so the cold-load cost is paid once
        per session rather than once per query.
        """
        if not self._server_ready:
            self._wait_for_ready()
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": temperature},
            }
            if num_predict:
                # Generation length is the dominant cost once the model is warm.
                # Answers are spoken in 1-3 sentences, so capping tokens cuts
                # latency without truncating anything the user wanted.
                payload["options"]["num_predict"] = num_predict
            if tools:
                payload["tools"] = tools

            response = requests.post(
                f"{self.ollama_url}/api/chat", json=payload, timeout=timeout
            )
            if response.status_code != 200:
                return {"error": f"Ollama API error: {response.status_code}"}
            return response.json().get("message", {}) or {}

        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _call_ollama(self, prompt, format_json=True):
        """
        Make API call to Ollama
        Returns parsed JSON or text response
        """
        if not self._server_ready:
            self._wait_for_ready()

        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False}
            if format_json:
                payload["format"] = "json"

            response = requests.post(self.api_endpoint, json=payload, timeout=120)

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "{}")

                if format_json:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # Fallback if JSON parsing fails
                        return {"error": "Invalid JSON response", "raw": response_text}
                else:
                    return response_text
            else:
                return {"error": f"Ollama API error: {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def extract_intent(self, user_speech):
        """
        Classify user intent from natural speech
        Returns: intent type (project_update/goal_update/todo_add/query/unknown)
        """
        prompt = f"""You are analyzing voice commands for a personal assistant. Classify the user's intent.

User said: "{user_speech}"

Classify into ONE of these intents:
- project_update: User is updating work on a project
- project_query: User is asking about a project
- goal_update: User is updating progress on a goal
- goal_query: User is asking about a goal
- todo_add: User wants to add a task
- todo_query: User is asking about todos
- unknown: Cannot determine intent

Return ONLY valid JSON:
{{
  "intent": "one of the above values",
  "confidence": "high/medium/low"
}}"""

        result = self._call_ollama(prompt, format_json=True)

        if "error" in result:
            return {"intent": "unknown", "confidence": "low", "error": result["error"]}

        return result

    def extract_project_info(self, user_speech):
        """
        Extract project-related information from user speech
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")

        prompt = f"""Extract project information from the user's statement. Today is {current_date}.

User said: "{user_speech}"

Extract and return ONLY valid JSON:
{{
  "project_name": "name of the project or null",
  "action": "completed/started/working_on/blocked/null",
  "update": "description of what was done",
  "component": "specific feature/module mentioned or null",
  "status": "in-progress/completed/blocked/on-hold or null",
  "time_spent": "time mentioned or null",
  "notes": "any additional context or null"
}}

Return ONLY the JSON, no explanation."""

        result = self._call_ollama(prompt, format_json=True)

        if "error" not in result:
            result["timestamp"] = f"{current_date} {current_time}"

        return result

    def extract_goal_info(self, user_speech):
        """
        Extract goal progress information from user speech
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""Extract goal/achievement information from the user's statement. Today is {current_date}.

User said: "{user_speech}"

Extract and return ONLY valid JSON:
{{
  "goal_name": "name/type of goal (e.g., push-ups, guitar practice, coding)",
  "value": 0,
  "unit": "unit of measurement (push-ups, hours, repos, etc)",
  "category": "fitness/skill/career/personal or null",
  "note": "any additional context or null"
}}

Return ONLY the JSON, no explanation."""

        result = self._call_ollama(prompt, format_json=True)

        if "error" not in result:
            result["date"] = current_date

        return result

    def extract_todo_info(self, user_speech):
        """
        Extract todo task information from user speech
        """
        prompt = f"""Extract task information from the user's statement.

User said: "{user_speech}"

Extract and return ONLY valid JSON:
{{
  "task": "the task description",
  "when": "today/tomorrow/specific_date or null",
  "priority": "high/medium/low or null",
  "project_linked": "project name if mentioned or null"
}}

Return ONLY the JSON, no explanation."""

        return self._call_ollama(prompt, format_json=True)

    def generate_natural_response(self, action_type, data):
        """
        Generate a natural, friendly response based on action taken

        action_type: 'project_updated', 'goal_updated', 'todo_added', etc.
        data: dict with relevant information
        """
        prompt = f"""You are Phoenix, a friendly personal assistant. Generate a short, encouraging response.

Action: {action_type}
Data: {json.dumps(data, indent=2)}

Generate a natural, friendly response (1-2 sentences max) that:
- Acknowledges what was done
- Is encouraging and professional
- Uses "sir" occasionally but not always
- Sounds human and warm

Return ONLY the response text, no JSON, no quotes."""

        response = self._call_ollama(prompt, format_json=False)

        # Clean up response if needed
        if isinstance(response, dict) and "error" in response:
            # Fallback responses
            fallback = {
                "project_updated": "Project updated successfully, sir!",
                "goal_updated": "Great progress! Goal updated.",
                "todo_added": "Task added to your list!",
                "project_queried": "Here's the project information.",
                "goal_queried": "Here's your goal status.",
            }
            return fallback.get(action_type, "Done, sir!")

        return response.strip()

    def check_ollama_status(self):
        """
        Check if Ollama is running and model is available
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                return {
                    "status": "online",
                    "model_available": self.model in model_names,
                    "available_models": model_names,
                }
            else:
                return {"status": "error", "message": "Ollama API not responding"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}


# Standalone testing
if __name__ == "__main__":
    print("Testing OllamaHelper...")

    helper = OllamaHelper()

    # Test 1: Check Ollama status
    print("\n[TEST 1] Checking Ollama status...")
    status = helper.check_ollama_status()
    print(f"Status: {json.dumps(status, indent=2)}")

    if status.get("status") != "online":
        print("❌ Ollama is not running. Please start Ollama first.")
        exit(1)

    # Test 2: Intent extraction
    print("\n[TEST 2] Testing intent extraction...")
    test_speech = "I'm working on Dukan project, completed the admin dashboard"
    intent = helper.extract_intent(test_speech)
    print(f"Intent: {json.dumps(intent, indent=2)}")

    # Test 3: Project info extraction
    print("\n[TEST 3] Testing project info extraction...")
    project_info = helper.extract_project_info(test_speech)
    print(f"Project Info: {json.dumps(project_info, indent=2)}")

    # Test 4: Natural response generation
    print("\n[TEST 4] Testing natural response...")
    response = helper.generate_natural_response("project_updated", project_info)
    print(f"Response: {response}")

    print("\n✅ All tests completed!")
