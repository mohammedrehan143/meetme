import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("meetme.agents.assignment")

AMBIGUOUS_TERMS = {
    "unassigned", "ambiguous", "tbd", "to be determined", "nobody", "no one",
    "someone", "anyone", "everybody", "everyone", "team", "n/a", "none",
    "unknown", "null", "undefined", "speaker", "whoever", "anybody", "unassigned (ambiguous)"
}

def clean_speaker_or_role(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = val.strip().strip(":").strip("-").strip()
    if val.lower() in AMBIGUOUS_TERMS:
        return None
    return val

class AssignmentAgent:
    """
    Matches extracted tasks to verified workspace members and assigns email addresses
    with high precision. When roles or candidate names are provided, preserves them
    accurately rather than falling back to 'Unassigned (Ambiguous)'.
    """
    def match_assignments(
        self,
        tasks: List[Dict[str, Any]],
        workspace_members: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        assigned_tasks = []

        # 1. Build rich lookup tables of workspace members
        member_by_fullname: Dict[str, Dict[str, Any]] = {}
        member_by_firstname: Dict[str, Dict[str, Any]] = {}
        member_by_email: Dict[str, Dict[str, Any]] = {}
        member_by_role: Dict[str, Dict[str, Any]] = {}
        member_by_title: Dict[str, Dict[str, Any]] = {}

        for m in workspace_members:
            full_name = (m.get("full_name") or "").strip()
            email = (m.get("email") or "").strip().lower()
            role = (m.get("role") or "").strip().lower()
            title = (m.get("title") or "").strip().lower()

            if full_name:
                fn_lower = full_name.lower()
                member_by_fullname[fn_lower] = m
                parts = fn_lower.split()
                if parts:
                    first = parts[0]
                    if first not in member_by_firstname:
                        member_by_firstname[first] = m
                    last = parts[-1]
                    if len(parts) > 1 and last not in member_by_firstname:
                        member_by_firstname[last] = m

            if email:
                member_by_email[email] = m
                email_handle = email.split("@")[0]
                if email_handle not in member_by_email:
                    member_by_email[email_handle] = m

            if role:
                member_by_role[role] = m
            if title:
                member_by_title[title] = m
                # Index key technical tokens
                for word in re.findall(r"[a-zA-Z]+", title):
                    w_lower = word.lower()
                    if len(w_lower) >= 3 and w_lower not in ["the", "and", "for", "with", "lead", "senior", "junior", "head", "manager"]:
                        if w_lower not in member_by_title:
                            member_by_title[w_lower] = m

        for task in tasks:
            raw_assignee = task.get("assignee")
            evidence = task.get("evidence", "")
            desc = task.get("description", "")
            title = task.get("title", "")

            # If assignee is missing or ambiguous, try to recover from evidence / speaker
            if not raw_assignee or raw_assignee.strip().lower() in AMBIGUOUS_TERMS:
                recovered = self._extract_speaker_or_owner_from_text(evidence, desc, title)
                if recovered:
                    raw_assignee = recovered

            clean_assignee = clean_speaker_or_role(raw_assignee)
            matched_member = None
            match_confidence = task.get("confidence", 0.90)

            if clean_assignee:
                target = clean_assignee.lower()

                # A. Direct email match
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_assignee)
                if email_match and email_match.group(0).lower() in member_by_email:
                    matched_member = member_by_email[email_match.group(0).lower()]
                    match_confidence = 0.98

                # B. Direct Full Name match
                if not matched_member and target in member_by_fullname:
                    matched_member = member_by_fullname[target]
                    match_confidence = 0.95

                # C. First Name match
                if not matched_member:
                    first_token = target.split()[0].strip("(),-:")
                    if first_token in member_by_firstname:
                        matched_member = member_by_firstname[first_token]
                        match_confidence = 0.90

                # D. Role / Title match (e.g. "DevOps Lead", "Product Manager", "Backend Engineer")
                if not matched_member:
                    role_sub = re.search(r"\((.*?)\)|\[(.*?)\]|- (.*?)$|: (.*?)$", clean_assignee)
                    extracted_role = (
                        role_sub.group(1) or role_sub.group(2) or role_sub.group(3) or role_sub.group(4)
                        if role_sub else None
                    )

                    if target in member_by_title:
                        matched_member = member_by_title[target]
                        match_confidence = 0.88
                    elif target in member_by_role:
                        matched_member = member_by_role[target]
                        match_confidence = 0.88

                    if not matched_member and extracted_role:
                        er_clean = extracted_role.strip().lower()
                        if er_clean in member_by_title:
                            matched_member = member_by_title[er_clean]
                            match_confidence = 0.88
                        elif er_clean in member_by_role:
                            matched_member = member_by_role[er_clean]
                            match_confidence = 0.88

                # E. Fuzzy / Substring match across full names
                if not matched_member:
                    for fn_key, m in member_by_fullname.items():
                        if fn_key in target or target in fn_key:
                            matched_member = m
                            match_confidence = min(match_confidence, 0.85)
                            break

                # F. Fuzzy title match
                if not matched_member:
                    for t_key, m in member_by_title.items():
                        if len(t_key) >= 4 and (t_key in target or target in t_key):
                            matched_member = m
                            match_confidence = min(match_confidence, 0.84)
                            break

            # 3. Apply assignment results
            if matched_member:
                task["assignee_id"] = matched_member.get("id")
                task["assignee_name"] = matched_member.get("full_name")
                task["assignee_email"] = matched_member.get("email")
                task["confidence"] = round(match_confidence, 2)
                task["requires_human_clarification"] = False
            elif clean_assignee:
                # Name or Role was explicitly provided, but person is not in WorkspaceMember database yet!
                # PRESERVE THE EXACT PERSON NAME AND/OR ROLE! DO NOT OVERWRITE TO UNASSIGNED!
                extracted_email = None
                em_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_assignee)
                if em_match:
                    extracted_email = em_match.group(0)

                task["assignee_id"] = None
                task["assignee_name"] = clean_assignee
                task["assignee_email"] = extracted_email
                task["confidence"] = round(max(match_confidence, 0.85), 2)
                task["requires_human_clarification"] = False
            else:
                # Truly unassigned action item
                task["assignee_id"] = None
                task["assignee_name"] = "Unassigned"
                task["assignee_email"] = None
                task["confidence"] = round(min(match_confidence, 0.60), 2)
                task["requires_human_clarification"] = True

            assigned_tasks.append(task)

        return assigned_tasks

    def _extract_speaker_or_owner_from_text(self, evidence: str, desc: str, title: str) -> Optional[str]:
        combined = f"{evidence}\n{desc}\n{title}"

        # 1. Look for explicit owner labels: "Assignee: Sarah", "Owner: DevOps Lead", "Assigned to: Alex"
        owner_match = re.search(r"(?:assignee|assigned to|owner|lead|poc):\s*([^,\n\.]+)", combined, re.IGNORECASE)
        if owner_match:
            candidate = owner_match.group(1).strip()
            if candidate.lower() not in AMBIGUOUS_TERMS:
                return candidate

        # 2. Look for speaker tag before colon in evidence: "[00:01:23] Alex (DevOps): ..." or "Sarah Chen: ..."
        for line in evidence.split("\n"):
            line = line.strip()
            speaker_match = re.match(r"^(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*)?([^:\n]+?):\s*(.*)$", line)
            if speaker_match:
                spk = speaker_match.group(2).strip()
                speech = speaker_match.group(3).lower()
                if spk.lower() not in AMBIGUOUS_TERMS:
                    # If speaker took commitment or spoke in first person
                    if any(c in speech for c in ["i will", "i'll", "i am going to", "i can", "i take", "my task", "on it"]):
                        return spk
                    # Or direct instruction "Alex, please deploy..."
                    inst_match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b,\s*(?:please|can you|could you|take care of)", line)
                    if inst_match and inst_match.group(1).lower() not in AMBIGUOUS_TERMS:
                        return inst_match.group(1).strip()
                    return spk
        return None

assignment_agent = AssignmentAgent()
