def handle(command: str):
    if command.strip().lower() == "plugin hello":
        return "Hello from the example plugin."
    return None
