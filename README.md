# AI Personal Desktop Assistant

A small Python desktop assistant with a GUI, typed commands, optional voice input, reminders, notes reading, web search, weather, and an optional LLM API hook.

## Features

- Open Chrome
- Tell weather
- Search Google
- Read notes from the `notes/` folder
- Set reminders
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

## Setup

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

## Optional LLM

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
take screenshot
summarize clipboard
rewrite clipboard
translate clipboard to Hindi
draft email I will be absent tomorrow
remember my college starts at 9 AM
what do you remember
quiz me
make flashcards
plugin hello
ask explain recursion simply
```

## Folders

- Put notes in `notes/`
- Put `.txt`, `.md`, or `.pdf` documents in `documents/`
- Screenshots are saved in `screenshots/`
- Add custom command files in `plugins/`
