from langchain_core.tools import tool
from pathlib import Path
from datetime import datetime


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """
    Send an email to a specified recipient.

    Args:
        recipient: The email address of the recipient.
        subject:   The subject line of the email.
        body:      The main content of the email.

    Returns:
        A status message indicating the result.
    """
    if not recipient or "@" not in recipient:
        return f"Sorry, '{recipient}' doesn't look like a valid email address. Please double-check and try again."

    if not subject.strip():
        return "It seems the subject line is empty. Could you provide a subject before sending?"

    if not body.strip():
        return "The email body appears to be empty. Please add some content before sending."

    # TODO: Integrate with an email provider (e.g. SendGrid, Gmail API)
    return (
        f"Thank you! Your email to {recipient} with the subject '{subject}' "
        f"has been queued, but email sending hasn't been configured yet. "
        f"Please set up an email provider to enable this feature."
    )


@tool
def add_note(content: str) -> str:
    """
    Save a note to the local notes file.

    Args:
        content: The text content of the note to be saved.

    Returns:
        A confirmation message or a helpful error description.
    """
    if not content.strip():
        return "It looks like your note is empty. Please provide some content to save."

    notes_path = Path("data/notes.txt")

    try:
        notes_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {content.strip()}\n"

        with notes_path.open("a", encoding="utf-8") as f:
            f.write(entry)

        return f"Your note has been saved successfully at {timestamp}. You can find it in '{notes_path}'."

    except PermissionError:
        return f"Sorry, I wasn't able to save your note — it seems there's a permission issue accessing '{notes_path}'. Please check the folder permissions."

    except OSError as e:
        return f"Something went wrong while saving your note: {e}. Please try again or check your storage."