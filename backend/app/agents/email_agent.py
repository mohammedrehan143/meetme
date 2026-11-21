import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("meetme.agents.email")

class EmailAgent:
    """
    Generates high-precision, executive-ready HTML & plain-text emails for assignments,
    reminders, overdue alerts, and meeting summaries.
    """
    def generate_task_assignment_email(
        self,
        task: Dict[str, Any],
        meeting_title: str,
        workspace_name: str = "Engineering Workspace"
    ) -> Dict[str, str]:
        title = task.get("title", "Action Item")
        assignee = task.get("assignee_name", "Team Member")
        deadline = task.get("deadline", "No deadline specified")
        priority = task.get("priority", "MEDIUM")
        evidence = task.get("evidence_quote") or task.get("evidence", "Extracted from meeting discussion.")
        description = task.get("description", "")

        priority_color = "#FF7900" if priority in ["HIGH", "URGENT"] else "#B6FF00"

        subject = f"[MEETME Action Required] Task Assigned: {title}"

        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 0; background-color: #090909; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #FFFFFF; }}
    .container {{ max-width: 600px; margin: 30px auto; background-color: #111111; border: 1px solid #303030; border-radius: 6px; overflow: hidden; }}
    .header {{ padding: 24px 28px; background-color: #191919; border-bottom: 1px solid #303030; }}
    .brand {{ font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #FF7900; text-transform: uppercase; }}
    .content {{ padding: 28px; }}
    .badge {{ display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border-radius: 4px; background-color: #202020; color: {priority_color}; border: 1px solid #303030; margin-bottom: 16px; }}
    .task-title {{ font-size: 20px; font-weight: 600; color: #FFFFFF; margin: 0 0 16px 0; line-height: 1.4; }}
    .meta-box {{ background-color: #191919; border: 1px solid #303030; border-radius: 4px; padding: 16px; margin: 20px 0; }}
    .meta-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }}
    .meta-label {{ color: #A0A0A0; }}
    .meta-val {{ color: #FFFFFF; font-weight: 500; }}
    .quote-box {{ border-left: 3px solid #FF7900; padding: 10px 16px; background-color: #161616; margin: 20px 0; font-style: italic; color: #CCCCCC; font-size: 13px; }}
    .footer {{ padding: 20px 28px; background-color: #0c0c0c; border-top: 1px solid #222222; font-size: 12px; color: #666666; text-align: center; }}
    .btn {{ display: inline-block; background-color: #FF7900; color: #090909; padding: 10px 20px; text-decoration: none; font-weight: 600; font-size: 13px; border-radius: 4px; margin-top: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">MEETME &bull; EXECUTION ENGINE</div>
    </div>
    <div class="content">
      <div class="badge">{priority} PRIORITY</div>
      <h2 class="task-title">{title}</h2>
      <p style="color: #A0A0A0; font-size: 14px; line-height: 1.6;">Hello {assignee}, an action item was identified during <strong>{meeting_title}</strong> and has been approved for execution.</p>
      
      <div class="meta-box">
        <div style="margin-bottom: 8px;"><span class="meta-label">Deadline: </span> <span class="meta-val" style="color: #FF7900;">{deadline}</span></div>
        <div style="margin-bottom: 8px;"><span class="meta-label">Source Meeting: </span> <span class="meta-val">{meeting_title}</span></div>
        <div><span class="meta-label">Workspace: </span> <span class="meta-val">{workspace_name}</span></div>
      </div>

      <div style="font-size: 12px; font-weight: 600; color: #A0A0A0; text-transform: uppercase; letter-spacing: 1px; margin-top: 20px;">Transcript Evidence</div>
      <div class="quote-box">&ldquo;{evidence}&rdquo;</div>

      {f'<p style="color: #A0A0A0; font-size: 13px; margin-top: 16px;">{description}</p>' if description else ''}
    </div>
    <div class="footer">
      Automated by MEETME &bull; Meetings in. Execution out.
    </div>
  </div>
</body>
</html>
"""
        text = f"""MEETME Action Item: {title}
Priority: {priority}
Assignee: {assignee}
Deadline: {deadline}
Source Meeting: {meeting_title}

Transcript Evidence:
"{evidence}"

Description: {description}
"""
        return {"subject": subject, "html": html, "text": text}

    def generate_reminder_email(
        self,
        task: Dict[str, Any],
        reminder_type: str = "PRE_DEADLINE"
    ) -> Dict[str, str]:
        title = task.get("title", "Action Item")
        assignee = task.get("assignee_name", "Team Member")
        deadline = task.get("deadline", "Approaching")

        if reminder_type == "OVERDUE":
            subject = f"[OVERDUE WARNING] Action Item Past Deadline: {title}"
            accent = "#FF3B30"
            heading = "Overdue Task Notice"
            desc = f"The following task assigned to you passed its deadline on {deadline} and remains incomplete."
        elif reminder_type == "DEADLINE_DAY":
            subject = f"[DUE TODAY] Action Item Due Today: {title}"
            accent = "#FF7900"
            heading = "Task Due Today"
            desc = f"Reminder that your action item is due today ({deadline})."
        else:
            subject = f"[REMINDER] Upcoming Deadline: {title}"
            accent = "#B6FF00"
            heading = "Upcoming Deadline Reminder"
            desc = f"Your assigned action item is due on {deadline}. Please ensure progress is on track."

        html = f"""
<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 0; background-color: #090909; font-family: -apple-system, sans-serif; color: #FFFFFF;">
  <div style="max-width: 600px; margin: 30px auto; background-color: #111111; border: 1px solid #303030; border-radius: 6px; padding: 28px;">
    <div style="font-size: 12px; font-weight: 700; letter-spacing: 2px; color: {accent}; text-transform: uppercase; margin-bottom: 8px;">{heading}</div>
    <h3 style="font-size: 18px; margin: 0 0 12px 0;">{title}</h3>
    <p style="color: #A0A0A0; font-size: 14px; line-height: 1.6;">Hello {assignee},<br>{desc}</p>
    <div style="background-color: #191919; border: 1px solid #303030; padding: 12px; border-radius: 4px; font-size: 13px; margin: 16px 0;">
      <span style="color: #A0A0A0;">Deadline: </span><strong style="color: {accent};">{deadline}</strong>
    </div>
    <div style="font-size: 11px; color: #666666; margin-top: 24px;">MEETME Reminder Engine &bull; Persistent Tracking</div>
  </div>
</body>
</html>
"""
        text = f"{heading}: {title}\nAssignee: {assignee}\nDeadline: {deadline}\n{desc}"
        return {"subject": subject, "html": html, "text": text}

    def generate_meeting_summary_email(
        self,
        meeting_title: str,
        summary: str,
        tasks_count: int,
        decisions: list
    ) -> Dict[str, str]:
        subject = f"[MEETME Summary] Executive Meeting Report: {meeting_title}"
        decisions_html = "".join([f"<li style='margin-bottom: 6px; color: #CCCCCC;'><strong>{d.get('title', '')}</strong>: {d.get('summary', '')}</li>" for d in decisions])
        
        html = f"""
<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 0; background-color: #090909; font-family: -apple-system, sans-serif; color: #FFFFFF;">
  <div style="max-width: 640px; margin: 30px auto; background-color: #111111; border: 1px solid #303030; border-radius: 6px; padding: 28px;">
    <div style="font-size: 12px; font-weight: 700; letter-spacing: 2px; color: #FF7900; text-transform: uppercase;">MEETME &bull; EXECUTIVE REPORT</div>
    <h2 style="font-size: 22px; margin: 8px 0 16px 0;">{meeting_title}</h2>
    <div style="background-color: #191919; border: 1px solid #303030; padding: 14px; border-radius: 4px; margin-bottom: 20px;">
      <span style="color: #B6FF00; font-weight: 700;">{tasks_count} Action Items Extracted</span> &bull; <span style="color: #A0A0A0;">{len(decisions)} Key Decisions</span>
    </div>
    <h4 style="color: #A0A0A0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Executive Summary</h4>
    <p style="color: #E0E0E0; font-size: 14px; line-height: 1.6;">{summary}</p>
    
    <h4 style="color: #A0A0A0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-top: 24px;">Key Decisions Finalized</h4>
    <ul style="font-size: 13px; padding-left: 20px;">
      {decisions_html or "<li style='color: #888;'>No formal decisions recorded.</li>"}
    </ul>
    <div style="font-size: 11px; color: #666666; margin-top: 24px;">Generated autonomously by MEETME.</div>
  </div>
</body>
</html>
"""
        text = f"MEETME Summary: {meeting_title}\n\nTasks Extracted: {tasks_count}\nDecisions: {len(decisions)}\n\nSummary:\n{summary}"
        return {"subject": subject, "html": html, "text": text}

email_agent = EmailAgent()
