import sys
import json
import getpass
import urllib.request
import os
from datetime import datetime
from pathlib import Path

# Paths (UPDATED TO V2 FOLDER)
LOG_DIR = Path.home() / ".lab_manager_v2"
SESSION_TRACKER = LOG_DIR / ".active_session"
OLLAMA_URL = "http://localhost:11434/api/generate"

def get_current_session_file():
    if SESSION_TRACKER.exists():
        with open(SESSION_TRACKER, 'r') as f:
            filepath = f.read().strip()
            if filepath:
                return Path(filepath)
    return LOG_DIR / "fallback_calendar.json"

def ensure_file(file_path):
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump([], f)

def append_to_json(entry_dict):
    active_log_file = get_current_session_file()
    ensure_file(active_log_file)
    try:
        with open(active_log_file, 'r') as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(entry_dict)
    with open(active_log_file, 'w') as f:
        json.dump(data, f, indent=4)

def init_session():
    print("\n" + "="*50)
    print(" 🧪 UoM Lab Manager V2 - Interactive Session Menu")
    print("="*50)
    existing_files = list(LOG_DIR.glob("*.json"))
    print("Select a Workspace:")
    print(" [0] ➕ Create a NEW session here")
    print(" [1] 📁 Link an existing JSON file via custom path")
    for idx, file in enumerate(existing_files, 2):
        print(f" [{idx}] 🔄 Continue: {file.name}")

    try:
        choice = input("\nEnter number: ").strip()
        if choice == "0":
            new_name = input("Enter new session name: ").strip()
            if not new_name.endswith('.json'): new_name += '.json'
            selected_path = LOG_DIR / new_name
        elif choice == "1":
            custom_path = input("Enter full path to JSON file: ").strip()
            selected_path = Path(custom_path).expanduser().resolve()
        else:
            selected_path = existing_files[int(choice) - 2]
    except Exception:
        selected_path = LOG_DIR / "default_session.json"

    ensure_file(selected_path)
    with open(SESSION_TRACKER, 'w') as f:
        f.write(str(selected_path))
    print(f"✅ Active session locked to: {selected_path}\n")

def call_ollama(prompt_text):
    payload = {"model": "mistral", "prompt": prompt_text, "stream": False}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['response'].strip()
    except Exception as e:
        return "Ollama Connection Error: Is the app running?"

def extract_parameters(command_text):
    params = {}
    parts = command_text.split()
    for i, part in enumerate(parts):
        if part.startswith('-'):
            key = part.lstrip('-')
            if i + 1 < len(parts) and not parts[i+1].startswith('-'):
                params[key] = parts[i+1]
            else:
                params[key] = "True"
    return params

def log_event(command_text, exit_code):
    status = "Success" if exit_code == "0" else "Failed"
    ai_response = "None"
    
    if status == "Failed":
        print(f"\n⚠️ [Error]: '{command_text}' failed.")
        print("🤖 Mistral is analyzing...\n")
        prompt = f"I ran '{command_text}' in terminal and it failed. In two short sentences, why did it fail and what is the fix?"
        ai_response = call_ollama(prompt)
        print(f"💡 Suggestion: {ai_response}\n")

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "user": getpass.getuser(),
        "command": command_text,
        "extracted_parameters": extract_parameters(command_text),
        "status": status,
        "ai_suggestion": ai_response
    }
    append_to_json(entry)

def read_file_content(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except Exception:
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(0)
    action = sys.argv[1]
    
    if action == "init":
        init_session()
        
    elif action == "log":
        log_event(sys.argv[2], sys.argv[3])
        
    elif action == "ask":
        raw_query = " ".join(sys.argv[2:])
        print("\n🤖 Thinking...")
        
        # FEATURE 1: Script Extraction
        if raw_query.startswith("--extract"):
            parts = raw_query.split()
            if len(parts) > 1:
                filename = parts[1]
                file_code = read_file_content(filename)
                if file_code:
                    prompt = f"Here is a script:\n\n{file_code}\n\nList all the command-line arguments this script accepts, what they do, and their default values."
                    ai_answer = call_ollama(prompt)
                else:
                    ai_answer = f"Error: Could not read {filename}"
            else:
                ai_answer = "Usage: ai --extract <filename>"
                
        # FEATURE 2: Script Modification
        elif raw_query.startswith("--modify"):
            parts = raw_query.split(" ", 2)
            if len(parts) >= 3:
                filename = parts[1]
                instruction = parts[2]
                file_code = read_file_content(filename)
                if file_code:
                    prompt = f"Here is a Python script:\n\n{file_code}\n\nTask: {instruction}\n\nRewrite the code to apply this change. Output the ENTIRE modified script from the first import to the last line. You MUST NOT use placeholders like '# ...' or 'rest of code remains unchanged'. Output ONLY the raw, complete Python code."
                    raw_code = call_ollama(prompt)
                    
                    # Clean code string logic explicitly fixed here
                    clean_code = raw_code.replace("```python", "").replace("```", "").strip()
                    new_filename = f"modified_{filename}"
                    
                    try:
                        with open(new_filename, 'w') as f:
                            f.write(clean_code)
                        ai_answer = f"✅ Successfully applied changes based on: '{instruction}'. Saved as {new_filename}."
                    except Exception as e:
                        ai_answer = f"Error saving file: {e}"
                else:
                    ai_answer = f"Error: Could not read {filename}"
            else:
                ai_answer = "Usage: ai --modify <filename> \"<your instructions>\""
                
        # FEATURE 3: Time-Travel RAG (Summarization)
        elif raw_query.startswith("--summarize"):
            question = raw_query.replace("--summarize", "").strip()
            active_log = get_current_session_file()
            try:
                with open(active_log, 'r') as f:
                    history_data = json.load(f)
                history_str = json.dumps(history_data, indent=2)
                prompt = f"Here is the user's terminal experiment history in JSON format:\n\n{history_str}\n\nBased ONLY on this history, answer the user's question: {question}"
                ai_answer = call_ollama(prompt)
            except Exception as e:
                ai_answer = f"Error reading history: {e}"
                
        # Standard Q&A
        else:
            prompt = f"I am a Mac user in the terminal. Provide the exact terminal command to do this: {raw_query}. Explain it briefly."
            ai_answer = call_ollama(prompt)
            
        print(f"\n💡 Answer:\n{ai_answer}\n")
        
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "user": getpass.getuser(),
            "command": f"[AI Query]: {raw_query}",
            "status": "AI Assistance",
            "ai_suggestion": ai_answer
        }
        append_to_json(entry)
