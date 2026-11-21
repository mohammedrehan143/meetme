import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("meetme.agents.assignment")

class AssignmentAgent:
    """
    Matches extracted tasks to verified workspace members and assigns email addresses
    with strict confidence scoring. Flags ambiguous ownership.
    """
    def match_assignments(
        self,
        tasks: List[Dict[str, Any]],
        workspace_members: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        assigned_tasks = []

        # Build lookup table of members by first name, full name, role
        member_lookup = {}
        for m in workspace_members:
            full_name = m.get("full_name", "").strip().lower()
            first_name = full_name.split()[0] if full_name else ""
            member_lookup[full_name] = m
            if first_name and first_name not in member_lookup:
                member_lookup[first_name] = m

        for task in tasks:
            assignee_str = task.get("assignee")
            evidence = task.get("evidence", "").lower()
            desc = task.get("description", "").lower()
            title = task.get("title", "").lower()

            matched_member = None
            match_confidence = task.get("confidence", 0.90)

            if assignee_str:
                clean_assignee = assignee_str.strip().lower()
                first = clean_assignee.split()[0] if clean_assignee else ""
                if clean_assignee in member_lookup:
                    matched_member = member_lookup[clean_assignee]
                elif first in member_lookup:
                    matched_member = member_lookup[first]
                else:
                    # Fuzzy match across names
                    for name_key, m in member_lookup.items():
                        if name_key in clean_assignee or clean_assignee in name_key:
                            matched_member = m
                            match_confidence = min(match_confidence, 0.82)
                            break
            
            # If assignee was explicitly None or task is inferred/ambiguous, do NOT assume speaker is the owner!
            if not matched_member and task.get("classification_type") != "INFERRED" and task.get("assignee"):
                for name_key, m in member_lookup.items():
                    if len(name_key) > 3 and (name_key in evidence or name_key in desc or name_key in title):
                        matched_member = m
                        match_confidence = 0.76
                        break

            # If no member matched or assignee was null -> Ambiguous
            if not matched_member:
                task["assignee_id"] = None
                task["assignee_name"] = "Unassigned (Ambiguous)"
                task["assignee_email"] = None
                task["confidence"] = min(match_confidence, 0.55)
                task["requires_human_clarification"] = True
            else:
                task["assignee_id"] = matched_member.get("id")
                task["assignee_name"] = matched_member.get("full_name")
                task["assignee_email"] = matched_member.get("email")
                task["confidence"] = round(match_confidence, 2)
                task["requires_human_clarification"] = match_confidence < 0.75

            assigned_tasks.append(task)

        return assigned_tasks

assignment_agent = AssignmentAgent()
