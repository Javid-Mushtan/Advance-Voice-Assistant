import time

from langchain_core.tools import tool
from pathlib import Path
from datetime import datetime

from src.tools.system_tools import open_app

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

import tkinter as tk

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

def get_contact_name():
    result = {"name": None}

    def submit():
        result["name"] = entry.get().strip()
        root.destroy()

    root = tk.Tk()
    root.title("WhatsApp Contact")
    root.geometry("300x120")

    tk.Label(root, text="Enter Contact Name:").pack(pady=10)

    entry = tk.Entry(root, width=30)
    entry.pack()
    entry.focus_force()

    entry.bind("<Return>", lambda event: submit())

    tk.Button(root, text="OK", command=submit).pack(pady=10)

    root.mainloop()

    return result["name"]

@tool
def send_whatsapp_message(contact_name: str, message: str) -> str:
    """
    Send a WhatsApp message to a contact by name (e.g. 'dad', 'mom').
    Searches for the contact inside WhatsApp itself - no phone number needed,
    but the name should be close to how the contact is actually saved.
    """
    if pyautogui is None:
        return "pyautogui isn't installed. Run: pip install pyautogui"
    if not contact_name.strip():
        return "I need a contact name to message."
    if not message.strip():
        return "I need a message to send."

    contact_name = get_contact_name()
    time.sleep(10)
    try:
        open_app.invoke({"app_name": "whatsapp"})
        time.sleep(2.5)

        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.6)
        pyautogui.typewrite(contact_name.strip(), interval=0.03)
        time.sleep(1.0)
        pyautogui.hotkey('down')
        pyautogui.press('enter')
        time.sleep(1.0)

        pyautogui.typewrite(message.strip(), interval=0.02)
        pyautogui.press('enter')

        return f"Sent '{message}' to {contact_name} on WhatsApp."
    except Exception as e:
        return f"Could not send WhatsApp message to {contact_name}: {str(e)}"

@tool
def open_whatsapp_chat_for_call(contact_name: str) -> str:
    """
    Open a WhatsApp contact's chat so a video/voice call can be started
    (e.g. user says 'video call dad'). Opens the right conversation but does
    NOT press the call button itself - the user taps it to start the call.
    """
    if pyautogui is None:
        return "pyautogui isn't installed. Run: pip install pyautogui"
    if not contact_name.strip():
        return "I need a contact name to open."

    contact_name = get_contact_name()
    time.sleep(10)
    try:
        open_app.invoke({"app_name": "whatsapp"})
        time.sleep(2.5)

        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.6)
        pyautogui.typewrite(contact_name.strip(), interval=0.03)
        time.sleep(1.0)
        pyautogui.press('down')
        pyautogui.press('enter')

        return f"Opened {contact_name}'s chat on WhatsApp - tap the video call icon to start the call."
    except Exception as e:
        return f"Could not open WhatsApp chat for {contact_name}: {str(e)}"
