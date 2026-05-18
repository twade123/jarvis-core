"""
Boardroom User Controls — detect natural language commands during meetings.

Detects: pause, resume, call_in, dismiss, redirect, end, breakout, direct_address
Returns structured control actions for the Meeting Broker.
"""

import re
import logging
from typing import Optional, Dict, List
from Handler.seat_registry import SEATS, get_all_seat_ids

logger = logging.getLogger("BoardroomControls")

# All seat IDs and their common names for NLP matching
_SEAT_NAMES = {}
for sid, seat in SEATS.items():
    _SEAT_NAMES[sid.lower()] = sid
    _SEAT_NAMES[seat["title"].lower()] = sid
    # Common abbreviations
    short = seat["title"].replace("Chief ", "").replace("Officer", "").strip().lower()
    _SEAT_NAMES[short] = sid

# Patterns for each control type
_PAUSE_PATTERNS = [
    r"\b(hold on|give me a (minute|moment|sec)|pause|wait|hang on|one sec|let me think)\b",
]

_RESUME_PATTERNS = [
    r"\b(okay continue|go ahead|resume|carry on|proceed|keep going|continue|back to it)\b",
]

_CALL_IN_PATTERNS = [
    r"\b(get|bring|call|add|include|pull in|we need)\b.{{0,30}}\b(the\s+)?({seats})\b",
    r"\b(we need|bring in|get)\b.{{0,20}}\b(legal|finance|marketing|security|engineering|sales|product|data|creative|operations|HR)\b",
]

_DISMISS_PATTERNS = [
    r"\b({seats})\b.{{0,20}}\b(you can go|not needed|dismissed|can leave|don't need)\b",
    r"\b(don't need|we're done with|dismiss|remove)\b.{{0,20}}\b(the\s+)?({seats})\b",
    r"\b(don't need|skip|we're good without)\b.{{0,20}}\b(risk|compliance|legal|finance|security|marketing)\b",
]

_REDIRECT_PATTERNS = [
    r"\b(let'?s focus on|let us focus on|pivot to|shift to|actually.*focus|change topic to|redirect to)\b",
    r"\b(forget about that|let's talk about|move on to)\b",
]

_END_PATTERNS = [
    r"\b(wrap it up|that's enough|let's execute|end the meeting|we're done|close it out|that'll do)\b",
    r"\b(okay.*synthesize|give me the plan|final summary)\b",
]

_BREAKOUT_PATTERNS = [
    r"\b({seats})\b.{{0,15}}\band\b.{{0,15}}\b({seats})\b.{{0,20}}\b(work.*out|hash.*out|figure.*out|discuss)\b",
]

_DIRECT_ADDRESS_PATTERNS = [
    r"@({seats})\b",
    r"\b({seats})\b[,:]",
    r"\b({seats})\b.{{0,5}}\bwhat do you (think|suggest|recommend)\b",
]


def _build_seats_pattern() -> str:
    """Build regex alternation for all seat IDs."""
    return "|".join(re.escape(sid) for sid in get_all_seat_ids())


def _find_seat_in_text(text: str) -> Optional[str]:
    """Find a seat ID mentioned in text. Returns uppercase seat ID or None."""
    text_lower = text.lower()
    # Check exact seat IDs first (most reliable)
    for sid in get_all_seat_ids():
        if sid.lower() in text_lower:
            return sid
    # Check role-based mentions
    role_to_seat = {
        "legal": "GC", "finance": "CFO", "marketing": "CMO",
        "security": "CISO", "engineering": "VPE", "sales": "CRvO",
        "product": "CPO", "data": "CDO", "creative": "CCO",
        "operations": "COO", "hr": "CHRO", "risk": "CRO",
        "strategy": "CSO", "experience": "CXO", "revenue": "CRvO",
    }
    for role, sid in role_to_seat.items():
        if role in text_lower:
            return sid
    return None


def detect_control(message: str, meeting_active: bool = True) -> Optional[Dict]:
    """
    Detect a boardroom control action in a user message.

    Returns dict with:
        action: pause|resume|call_in|dismiss|redirect|end|breakout|direct_address
        seat: (for call_in, dismiss, direct_address) seat ID
        seats: (for breakout) list of two seat IDs
        focus: (for redirect) the new topic focus
    Or None if no control detected.
    """
    if not meeting_active:
        return None

    seats_pattern = _build_seats_pattern()
    msg = message.strip()
    msg_lower = msg.lower()

    # Check pause
    for pat in _PAUSE_PATTERNS:
        if re.search(pat, msg_lower):
            return {"action": "pause"}

    # Check resume
    for pat in _RESUME_PATTERNS:
        if re.search(pat, msg_lower):
            return {"action": "resume"}

    # Check end
    for pat in _END_PATTERNS:
        if re.search(pat, msg_lower):
            return {"action": "end"}

    # Check call-in
    for pat in _CALL_IN_PATTERNS:
        compiled = pat.format(seats=seats_pattern)
        m = re.search(compiled, msg_lower, re.IGNORECASE)
        if m:
            seat = _find_seat_in_text(msg)
            if seat:
                return {"action": "call_in", "seat": seat}

    # Check dismiss
    for pat in _DISMISS_PATTERNS:
        compiled = pat.format(seats=seats_pattern)
        m = re.search(compiled, msg_lower, re.IGNORECASE)
        if m:
            seat = _find_seat_in_text(msg)
            if seat:
                return {"action": "dismiss", "seat": seat}

    # Check redirect
    for pat in _REDIRECT_PATTERNS:
        if re.search(pat, msg_lower):
            # Extract the focus topic (everything after the trigger phrase)
            focus = re.sub(pat, "", msg_lower).strip()
            return {"action": "redirect", "focus": focus or msg}

    # Check direct address
    for pat in _DIRECT_ADDRESS_PATTERNS:
        compiled = pat.format(seats=seats_pattern)
        m = re.search(compiled, msg, re.IGNORECASE)
        if m:
            seat = _find_seat_in_text(msg)
            if seat:
                return {"action": "direct_address", "seat": seat}

    # Check breakout (two seats + work it out)
    for pat in _BREAKOUT_PATTERNS:
        compiled = pat.format(seats=seats_pattern)
        m = re.search(compiled, msg, re.IGNORECASE)
        if m:
            # Find both seats
            found = []
            for sid in get_all_seat_ids():
                if sid.lower() in msg_lower and sid not in found:
                    found.append(sid)
                if len(found) == 2:
                    break
            if len(found) == 2:
                return {"action": "breakout", "seats": found}

    return None
