from getpass import getpass
from pathlib import Path


def main() -> None:
    print("OpenAI API key setup")
    print("Your key will be saved locally in .env and ignored by Git.")
    api_key = getpass("Paste your OpenAI API key: ").strip()

    if not api_key:
        print("No key entered. Nothing changed.")
        return

    model = input("Model [gpt-4o-mini]: ").strip() or "gpt-4o-mini"
    Path(".env").write_text(
        f'OPENAI_API_KEY="{api_key}"\nOPENAI_MODEL="{model}"\n',
        encoding="utf-8",
    )
    print(".env saved. Now run: python main.py")


if __name__ == "__main__":
    main()
