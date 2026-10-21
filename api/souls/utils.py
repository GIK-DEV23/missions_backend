"""Utility functions for the souls module."""


def mask_phone_number(phone: str | None) -> str | None:
    """
    Mask a phone number, showing only the last 4 digits.
    
    Examples:
        +254789456321 -> +254*****6321
        0712345678 -> 0******5678
        None -> None
    """
    if not phone:
        return None
    
    phone_str = str(phone)
    
    # Remove any spaces for processing
    clean_phone = phone_str.replace(" ", "")
    
    if len(clean_phone) <= 4:
        return clean_phone
    
    # Keep country code prefix (+ and first digits) and last 4 digits visible
    if clean_phone.startswith("+"):
        # International format: +254789456321 -> +254*****6321
        # Show country code (first 4 chars including +) and last 4 digits
        prefix_length = 4  # +254
        if len(clean_phone) <= prefix_length + 4:
            return clean_phone
        
        prefix = clean_phone[:prefix_length]
        suffix = clean_phone[-4:]
        masked_length = len(clean_phone) - prefix_length - 4
        return f"{prefix}{'*' * masked_length}{suffix}"
    else:
        # Local format: 0712345678 -> 0******5678
        # Show first digit and last 4 digits
        prefix = clean_phone[0]
        suffix = clean_phone[-4:]
        masked_length = len(clean_phone) - 1 - 4
        return f"{prefix}{'*' * masked_length}{suffix}"
