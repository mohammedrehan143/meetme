import logging
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

logger = logging.getLogger("meetme.agents.email")

class EmailAgent:
    """
    Generates high-precision, executive-ready HTML & plain-text emails for assignments,
    consolidated reminders, overdue alerts, and meeting summaries.
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
        task_id = task.get("id") or task.get("task_id", "")
        
        task_link = f"{settings.APP_FRONTEND_URL}/tasks"

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
    .btn {{ display: inline-block; background-color: #FF7900; color: #090909; padding: 10px 20px; text-decoration: none; font-weight: 700; font-size: 12px; border-radius: 4px; margin-top: 16px; text-transform: uppercase; letter-spacing: 1px; }}
    .footer {{ padding: 20px 28px; background-color: #0c0c0c; border-top: 1px solid #222222; font-size: 12px; color: #666666; text-align: center; }}
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

      <div style="margin-top: 24px;">
        <a href="{task_link}" class="btn" style="color: #090909;">View Task in MEETME Dashboard &rarr;</a>
      </div>
    </div>
    <div class="footer">
      Automated by MEETME native Gmail SMTP Engine &bull; Meetings in. Execution out.
    </div>
  </div>
</body>
</html>
"""
        text = f"""MEETME Action Item Assigned: {title}
Priority: {priority}
Assignee: {assignee}
Deadline: {deadline}
Source Meeting: {meeting_title}

Transcript Evidence:
"{evidence}"

Description: {description}

View Task in MEETME Dashboard: {task_link}
"""
        return {"subject": subject, "html": html, "text": text}

    def generate_single_reminder_email(
        self,
        task: Dict[str, Any],
        reminder_type: str = "PRE_DEADLINE"
    ) -> Dict[str, str]:
        title = task.get("title", "Action Item")
        assignee = task.get("assignee_name", "Team Member")
        deadline = task.get("deadline", "Approaching")
        task_link = f"{settings.APP_FRONTEND_URL}/tasks"

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
            subject = f"[REMINDER] Upcoming Deadline (24h): {title}"
            accent = "#B6FF00"
            heading = "Upcoming Deadline Reminder (24 Hours)"
            desc = f"Your assigned action item is due tomorrow on {deadline}. Please verify execution progress."

        html = f"""
<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 0; background-color: #090909; font-family: -apple-system, sans-serif; color: #FFFFFF;">
  <div style="max-width: 600px; margin: 30px auto; background-color: #111111; border: 1px solid #303030; border-radius: 6px; padding: 28px;">
    <div style="font-size: 12px; font-weight: 700; letter-spacing: 2px; color: {accent}; text-transform: uppercase; margin-bottom: 8px;">{heading}</div>
    <h3 style="font-size: 18px; margin: 0 0 12px 0;">{title}</h3>
    <p style="color: #A0A0A0; font-size: 14px; line-height: 1.6;">Hello {assignee},<br>{desc}</p>
    <div style="background-color: #191919; border: 1px solid #303030; padding: 12px; border-radius: 4px; font-size: 13px; margin: 16px 0;">
      <span style="color: #A0A0A0;">Target Deadline: </span><strong style="color: {accent};">{deadline}</strong>
    </div>
    <div style="margin-top: 20px;">
      <a href="{task_link}" style="display: inline-block; background-color: {accent}; color: #090909; padding: 8px 16px; font-weight: 700; font-size: 12px; text-decoration: none; border-radius: 4px;">Update Task Status &rarr;</a>
    </div>
    <div style="font-size: 11px; color: #666666; margin-top: 24px;">MEETME Reminder Engine &bull; Native Gmail SMTP &bull; Persistent Tracking</div>
  </div>
</body>
</html>
"""
        text = f"{heading}: {title}\nAssignee: {assignee}\nDeadline: {deadline}\n{desc}\n\nDashboard: {task_link}"
        return {"subject": subject, "html": html, "text": text}

    def generate_consolidated_reminder_email(
        self,
        recipient_name: str,
        tasks: List[Dict[str, Any]],
        reminder_type: str = "PRE_DEADLINE"
    ) -> Dict[str, str]:
        """
        Consolidated Email Template:
        Groups multiple tasks due for the same recipient into ONE unified executive email.
        """
        task_link = f"{settings.APP_FRONTEND_URL}/tasks"
        count = len(tasks)

        if reminder_type == "OVERDUE":
            subject = f"[OVERDUE DIGEST] {count} Tasks Require Immediate Attention"
            accent = "#FF3B30"
            heading = f"{count} Overdue Tasks Notice"
            desc = f"You have {count} action items that have passed their deadline and remain incomplete."
        elif reminder_type == "DEADLINE_DAY":
            subject = f"[DUE TODAY] {count} Action Items Due Today"
            accent = "#FF7900"
            heading = f"{count} Tasks Due Today"
            desc = f"You have {count} action items scheduled for delivery today."
        else:
            subject = f"[REMINDER DIGEST] {count} Tasks Approaching Deadline Tomorrow"
            accent = "#B6FF00"
            heading = f"{count} Upcoming Tasks (24-Hour Reminder)"
            desc = f"The following {count} action items assigned to you are due tomorrow."

        # Build items table
        task_rows_html = ""
        task_rows_text = ""

        for idx, t in enumerate(tasks, 1):
            prio = t.get("priority", "MEDIUM")
            prio_color = "#FF7900" if prio in ["HIGH", "URGENT"] else "#B6FF00"
            t_title = t.get("title", "Action Item")
            t_deadline = t.get("deadline", "Pending")

            task_rows_html += f"""
            <tr style="border-bottom: 1px solid #262626;">
              <td style="padding: 12px 10px; color: #FFFFFF; font-weight: 500; font-size: 13px;">{t_title}</td>
              <td style="padding: 12px 10px; text-align: center;">
                <span style="display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 700; border-radius: 3px; background-color: #202020; color: {prio_color}; border: 1px solid #333;">{prio}</span>
              </td>
              <td style="padding: 12px 10px; text-align: right; color: {accent}; font-family: monospace; font-size: 12px; font-weight: 600;">{t_deadline}</td>
            </tr>
            """
            task_rows_text += f"{idx}. {t_title} | Priority: {prio} | Due: {t_deadline}\n"

        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 0; background-color: #090909; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #FFFFFF; }}
    .container {{ max-width: 640px; margin: 30px auto; background-color: #111111; border: 1px solid #303030; border-radius: 6px; overflow: hidden; }}
    .header {{ padding: 20px 28px; background-color: #191919; border-bottom: 1px solid #303030; }}
    .brand {{ font-size: 12px; font-weight: 700; letter-spacing: 2px; color: {accent}; text-transform: uppercase; }}
    .content {{ padding: 28px; }}
    .table {{ width: 100%; border-collapse: collapse; margin-top: 16px; background-color: #161616; border: 1px solid #262626; border-radius: 4px; }}
    .th {{ padding: 10px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #888; background-color: #1c1c1c; border-bottom: 1px solid #303030; }}
    .btn {{ display: inline-block; background-color: {accent}; color: #090909; padding: 10px 20px; text-decoration: none; font-weight: 700; font-size: 12px; border-radius: 4px; margin-top: 24px; text-transform: uppercase; letter-spacing: 1px; }}
    .footer {{ padding: 16px 28px; background-color: #0c0c0c; border-top: 1px solid #222222; font-size: 11px; color: #666666; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">MEETME &bull; CONSOLIDATED EXECUTION REMINDER</div>
    </div>
    <div class="content">
      <h2 style="font-size: 18px; margin: 0 0 8px 0; color: #FFFFFF;">{heading}</h2>
      <p style="color: #A0A0A0; font-size: 13px; line-height: 1.6; margin: 0 0 16px 0;">Hello {recipient_name},<br>{desc}</p>
      
      <table class="table">
        <thead>
          <tr>
            <th class="th">Action Item</th>
            <th class="th" style="text-align: center;">Priority</th>
            <th class="th" style="text-align: right;">Deadline</th>
          </tr>
        </thead>
        <tbody>
          {task_rows_html}
        </tbody>
      </table>

      <div>
        <a href="{task_link}" class="btn" style="color: #090909;">Open MEETME Task Ledger ({count} Tasks) &rarr;</a>
      </div>
    </div>
    <div class="footer">
      Consolidated by MEETME Native Reminder Engine &bull; Zero Spam &bull; Meetings in. Execution out.
    </div>
  </div>
</body>
</html>
"""
        text = f"""MEETME Consolidated Reminder: {heading}
Recipient: {recipient_name}
{desc}

Tasks List:
{task_rows_text}

Update in MEETME Dashboard: {task_link}
"""
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
        dashboard_link = f"{settings.APP_FRONTEND_URL}/meetings"

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
    <div style="margin-top: 24px;">
      <a href="{dashboard_link}" style="display: inline-block; background-color: #FF7900; color: #090909; padding: 10px 20px; font-weight: 700; font-size: 12px; text-decoration: none; border-radius: 4px;">View Full Meeting Details &rarr;</a>
    </div>
    <div style="font-size: 11px; color: #666666; margin-top: 24px;">Dispatched autonomously via native Gmail SMTP Engine.</div>
  </div>
</body>
</html>
"""
        text = f"MEETME Summary: {meeting_title}\n\nTasks Extracted: {tasks_count}\nDecisions: {len(decisions)}\n\nSummary:\n{summary}\n\nDashboard: {dashboard_link}"
        return {"subject": subject, "html": html, "text": text}

email_agent = EmailAgent()
