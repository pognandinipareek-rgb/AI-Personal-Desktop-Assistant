# Nova

Nova is a polished Python desktop assistant with a GUI, typed commands, optional voice input, reminders, notes reading, web search, weather, demo AI mode, and optional AI through Ollama or OpenAI.

## Features

- Open Chrome
- Tell weather
- Search Google
- Read notes from the `notes/` folder
- Set reminders
- View and cancel reminders
- Open common apps and websites
- Search YouTube and Amazon
- Text-to-speech replies
- Conversation history
- Personal memory
- File search
- Folder shortcuts
- Screenshots
- Clipboard summarize/rewrite/translate
- Gmail draft helper
- Basic document/PDF reader
- Study quiz and flashcard helpers
- Simple plugin system
- Optional speech recognition
- Optional LLM responses through an OpenAI-compatible API
- Free local AI with Ollama
- Demo AI mode for GitHub users without an API key
- Settings window for default city, model, voice replies, and demo mode
- Double-click `install.bat` and `run.bat` scripts on Windows

## Setup

Easy Windows setup:

```powershell
install.bat
run.bat
```

Manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Speech recognition is optional. If `SpeechRecognition` or microphone support is unavailable, the app still works with typed commands.

## Run

```powershell
python main.py
```

Or double-click `run.bat`.

## Optional LLM

Free local AI with Ollama:

```powershell
ollama pull qwen2.5-coder:1.5b
python main.py
```

The assistant will try OpenAI first if configured, then Ollama local AI, then demo mode.

Option 1: run the helper:

```powershell
python setup_api_key.py
python main.py
```

Option 2: set environment variables before running:

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_MODEL="gpt-4o-mini"
python main.py
```

Option 3: copy `.env.example` to `.env` and put your key there. Never share or commit your real `.env` file.

## Example Commands

```text
open chrome
weather in Mumbai
search google Python Tkinter assistant
search youtube Python speech recognition
search amazon wireless keyboard
open gmail
open notepad
open folder downloads
read my notes
read my document
find file resume
set reminder in 10 minutes drink water
remind me to call mom after 20 minutes
show reminders
cancel reminder 1
take screenshot
summarize clipboard
rewrite clipboard
translate clipboard to Hindi
draft email I will be absent tomorrow
remember my college starts at 9 AM
what do you remember
quiz me
make flashcards
settings
set default city Delhi
ollama on
set ollama model qwen2.5-coder:1.5b
demo mode on
demo mode off
plugin hello
ask explain recursion simply
```

## GitHub Demo Mode

Demo mode is on by default. If the OpenAI API key is missing or quota is unavailable, the assistant still gives useful sample answers for common prompts such as recursion code, emails, quizzes, and flashcards. This makes the project easier for visitors to try before configuring an API key.

## Folders

- Put notes in `notes/`
- Put `.txt`, `.md`, or `.pdf` documents in `documents/`
- Screenshots are saved in `screenshots/`
- Add custom command files in `plugins/`
