from typing import List

class PromptSafetyFilter:
    FORBIDDEN_KEYWORDS: List[str] = ["bomb", "kill", "terrorist"]

    def is_unsafe(self, message: str) -> bool:
        """
        Checks if the message contains any forbidden keywords.
        The check is case-insensitive and considers partial matches.
        """
        if not message:
            return False
        
        processed_message = message.lower().strip()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword.lower() in processed_message:
                return True
        return False
