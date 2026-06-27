import os
import json
import logging
import time
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from lyra.system.context import build_context_string
from lyra.system.tools import AVAILABLE_TOOLS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

SYSTEM_PROMPT = """You are LYRA (Logical Yielding Reasoning Agent), a highly advanced, JARVIS-style AI terminal assistant.
You are elegant, precise, highly capable, and slightly witty but always professional.
You speak with a warm, precise British accent (Sonia).

You have deep access to the user's system and context.
You can execute commands, manage applications, browse the web, and control the system using the tools provided to you.
ALWAYS use the provided tools to fulfill user requests if applicable (e.g., if asked to open an app, use open_app).
If the user asks a question about their system state, check your context or use a tool.

When using tools, you don't need to explain every step, just do it and report the result naturally.
When answering general questions, be concise and to the point. No rambling.

{context_placeholder}
"""

class LyraAI:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "paste_your_api_key_here":
            logging.warning("GEMINI_API_KEY not found in environment or .env file.")
            
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3.1-flash-lite"
        
        self.history_file = Path.home() / ".lyra" / "history.jsonl"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.conversation_history = []
        self.chat_session = None
        
        self.load_history()
        self.init_chat()

    def get_system_instruction(self):
        context = build_context_string()
        return SYSTEM_PROMPT.replace("{context_placeholder}", context)

    def load_history(self):
        """Loads the last 10 exchanges (20 messages: user+model) from jsonl."""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            exchanges = []
            for line in lines[-10:]: # Get last 10 exchanges
                if line.strip():
                    exchanges.append(json.loads(line))
                    
            for ex in exchanges:
                # In google-genai, history is a list of types.Content
                self.conversation_history.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=ex.get("user", ""))])
                )
                self.conversation_history.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=ex.get("lyra", ""))])
                )
        except Exception as e:
            logging.error(f"Failed to load history: {e}")

    def save_exchange(self, user_text: str, model_text: str):
        """Saves a single exchange to the jsonl file."""
        import datetime
        exchange = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user_text,
            "lyra": model_text
        }
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(exchange) + "\n")
        except Exception as e:
            logging.error(f"Failed to save exchange: {e}")

    def init_chat(self):
        """Initializes the chat session with current context and history."""
        # Enforce rolling history: last 20 exchanges = 40 messages
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
            
        self.chat_session = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                tools=AVAILABLE_TOOLS,
                system_instruction=self.get_system_instruction(),
            ),
            history=self.conversation_history
        )

    def refresh_context(self):
        """Refreshes the context and re-initializes the chat."""
        # Update the history property of the chat session with the new system instruction isn't directly possible,
        # so we recreate the chat session.
        self.init_chat()

    def forget_last(self) -> str:
        """Forgets the last exchange."""
        if len(self.conversation_history) >= 2:
            self.conversation_history = self.conversation_history[:-2]
            self.init_chat()
            return "Consider it forgotten, sir."
        return "I have no recent memory to forget."

    def send_message_with_tools(self, text: str, ask_confirmation_callback=None) -> str:
        """Sends a message, explicitly handling function calls manually."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.chat_session.send_message(text)
                
                # Loop while model wants to call functions
                while response.function_calls:
                    function_responses = []
                    for tool_call in response.function_calls:
                        func_name = tool_call.name
                        # Handle args which can be a dict in the new SDK
                        args = tool_call.args if isinstance(tool_call.args, dict) else {}
                        
                        logging.info(f"LYRA is calling tool: {func_name} with args: {args}")
                        
                        # Intercept run_command for confirmation
                        if func_name == "run_command" and ask_confirmation_callback:
                            cmd = args.get("cmd", "")
                            confirmed = ask_confirmation_callback(cmd)
                            if not confirmed:
                                function_responses.append(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": "User denied permission to run command."}
                                    )
                                )
                                continue

                        # Execute the tool
                        func_ptr = next((f for f in AVAILABLE_TOOLS if f.__name__ == func_name), None)
                        if func_ptr:
                            try:
                                result = func_ptr(**args)
                                function_responses.append(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": str(result)}
                                    )
                                )
                            except Exception as ex:
                                function_responses.append(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"error": str(ex)}
                                    )
                                )
                        else:
                            function_responses.append(
                                types.Part.from_function_response(
                                    name=func_name,
                                    response={"error": "Tool not found."}
                                )
                            )
                    
                    # Send the tool responses back to the model
                    response = self.chat_session.send_message(function_responses)
                
                # Save to history once final text response is received
                if response.text:
                    self.save_exchange(text, response.text)
                    
                return response.text
                
            except APIError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    wait_time = 20 * (attempt + 1)
                    logging.warning(f"API Rate limit exceeded (429). Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Gemini API Error: {e}")
                    if e.code == 429:
                        return "I apologize, but my API rate limit has been exceeded. Please wait a minute or two before trying again."
                    return f"I encountered a system error: {e}"
            except Exception as e:
                logging.error(f"Unexpected Error: {e}")
                return f"I encountered an unexpected system error: {e}"
