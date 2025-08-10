import re
from datetime import datetime
from typing import List, Optional, Dict

from app.schemas.chat import ParsedMessageTemp

# Regex to match WhatsApp chat message format.
# This pattern tries to be robust for common formats:
# [DD/MM/YY, HH:MM:SS] Author: Message
# [DD/MM/YYYY, HH:MM:SS] Author: Message
# [DD.MM.YY, HH:MM:SS] Author: Message (some regional variations)
# Handles multi-line messages and omitted media.
# Date format: (\[\d{1,2}[/\.]\d{1,2}[/\.]\d{2,4}, \d{1,2}:\d{2}:\d{2}\])
# Author: ([^:]+):
# Message: (.*)
MESSAGE_PATTERN = re.compile(
    r"^\[(\d{1,2}[/\.]\d{1,2}[/\.]\d{2,4}), (\d{1,2}:\d{2}:\d{2})\] ([^:]+): (.*)",
    re.MULTILINE
)
# Pattern to identify omitted media within a message
MEDIA_OMITTED_PATTERN = re.compile(r"<Media omitted>\s*\(?([\w\s\-\._]+\.(?:jpg|jpeg|png|gif|mp4|mov|avi|3gp|m4a|mp3|aac|pdf|doc|docx|xls|xlsx|ppt|pptx))?\)?")
# Pattern for attached file names (e.g., from Android "Export chat with media")
ATTACHMENT_FILENAME_PATTERN = re.compile(r"(\S+\.(?:jpg|jpeg|png|gif|mp4|mov|avi|3gp|m4a|mp3|aac|pdf|doc|docx|xls|xlsx|ppt|pptx)) \(file attached\)")


def parse_whatsapp_chat(raw_chat_text: str) -> List[ParsedMessageTemp]:
    """
    Parses raw WhatsApp chat text into structured message objects.
    Handles date, author, message, and attempts to extract attachment filenames.
    """
    messages: List[ParsedMessageTemp] = []
    current_message_lines = []
    current_message_data = None

    for line in raw_chat_text.splitlines():
        match = MESSAGE_PATTERN.match(line)
        if match:
            # New message starts
            if current_message_data:
                # Process the previous message if it exists
                process_and_add_message(messages, current_message_data, current_message_lines)

            date_str, time_str, author, message_content = match.groups()
            
            # Attempt to parse date in multiple formats
            dt_obj = None
            # Common formats: DD/MM/YY, DD/MM/YYYY, DD.MM.YY, DD.MM.YYYY
            # WhatsApp also uses 24-hour format
            date_formats = [
                "%d/%m/%y, %H:%M:%S",
                "%d/%m/%Y, %H:%M:%S",
                "%d.%m.%y, %H:%M:%S",
                "%d.%m.%Y, %H:%M:%S",
                "%m/%d/%y, %H:%M:%S", # US format
                "%m/%d/%Y, %H:%M:%S"
            ]
            
            for fmt in date_formats:
                try:
                    dt_obj = datetime.strptime(f"{date_str}, {time_str}", fmt)
                    break
                except ValueError:
                    continue
            
            if dt_obj is None:
                # If date parsing fails, skip this message and log
                logger.warning(f"Failed to parse date for line: {line[:50]}...")
                current_message_data = None # Reset to avoid appending to invalid message
                current_message_lines = []
                continue

            current_message_data = {
                "date": dt_obj,
                "author": author.strip(),
                "message": message_content.strip(),
                "attachment": None # Will be populated if found
            }
            current_message_lines = []
        elif current_message_data:
            # Continuation of the previous message
            current_message_lines.append(line.strip())
        # else: line doesn't match and no current message, skip or log

    # Process the last message after the loop
    if current_message_data:
        process_and_add_message(messages, current_message_data, current_message_lines)

    return messages

def process_and_add_message(messages: List[ParsedMessageTemp], msg_data: Dict, extra_lines: List[str]):
    full_message = msg_data["message"]
    if extra_lines:
        full_message += "\n" + "\n".join(extra_lines)

    attachment_filename = None

    # Try to find <Media omitted> type attachments
    # This regex is more robust to capture the filename within or without parentheses
    media_omitted_match = MEDIA_OMITTED_PATTERN.search(full_message)
    if media_omitted_match:
        # Group 1 captures the filename if present, otherwise it's None or empty string
        attachment_filename = media_omitted_match.group(1) if media_omitted_match.group(1) else "media_omitted"
        full_message = MEDIA_OMITTED_PATTERN.sub("", full_message).strip() # Remove media tag from message text

    # Try to find specific filename attachments (often seen with Android exports like "IMG-XXXX.jpg (file attached)")
    # This might override `media_omitted` if a more specific filename is found.
    attachment_filename_match = ATTACHMENT_FILENAME_PATTERN.search(full_message)
    if attachment_filename_match:
        attachment_filename = attachment_filename_match.group(1)
        full_message = ATTACHMENT_FILENAME_PATTERN.sub("", full_message).strip() # Remove attachment tag

    messages.append(
        ParsedMessageTemp(
            date=msg_data["date"],
            author=msg_data["author"],
            message=full_message.strip(),
            attachment=attachment_filename # This will be the filename in the zip
        )
    )