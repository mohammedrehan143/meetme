import base64
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("meetme.services.jira")

class JiraService:
    """
    Real Jira Cloud REST API integration.
    Authenticates with Jira API token over HTTPS Port 443.
    """

    def _get_auth_header(self, email: str, api_token: str) -> str:
        credentials = f"{email}:{api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def test_connection(self, domain: str, email: str, api_token: str) -> Dict[str, Any]:
        """
        Validates authentication with Atlassian Jira Cloud instance.
        """
        clean_domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if not clean_domain.endswith(".atlassian.net"):
            clean_domain = f"{clean_domain}.atlassian.net"

        url = f"https://{clean_domain}/rest/api/3/myself"
        headers = {
            "Authorization": self._get_auth_header(email, api_token),
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    display_name = data.get("displayName", email)
                    return {
                        "success": True,
                        "domain": clean_domain,
                        "display_name": display_name,
                        "message": f"Successfully connected to Jira Cloud ({clean_domain}) as {display_name}."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Jira authentication failed ({resp.status_code}): {resp.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Jira connection error: {str(e)}"
            }

    async def create_issue(
        self,
        domain: str,
        email: str,
        api_token: str,
        project_key: str,
        title: str,
        description: str,
        issue_type: str = "Task",
        priority: str = "Medium",
        duedate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an actual Jira issue from an approved MEETME task.
        Uses ADF (Atlassian Document Format) for Jira v3.
        """
        clean_domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if not clean_domain.endswith(".atlassian.net"):
            clean_domain = f"{clean_domain}.atlassian.net"

        url = f"https://{clean_domain}/rest/api/3/issue"
        headers = {
            "Authorization": self._get_auth_header(email, api_token),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Construct Jira v3 payload
        fields: Dict[str, Any] = {
            "project": {"key": project_key.upper()},
            "summary": title[:255],
            "issuetype": {"name": issue_type},
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": description or title}
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Extracted & approved autonomously via MEETME Platform.", "marks": [{"type": "italic"}]}
                        ]
                    }
                ]
            }
        }

        # Map deadline if format YYYY-MM-DD
        if duedate and len(duedate) == 10 and duedate.count("-") == 2:
            fields["duedate"] = duedate

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json={"fields": fields})
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    issue_key = data.get("key")
                    issue_id = data.get("id")
                    issue_url = f"https://{clean_domain}/browse/{issue_key}"
                    logger.info(f"Created Jira issue {issue_key}: {issue_url}")
                    return {
                        "success": True,
                        "issue_key": issue_key,
                        "issue_id": issue_id,
                        "issue_url": issue_url,
                        "provider": "JIRA"
                    }
                else:
                    err_msg = f"Failed to create Jira issue ({resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    return {
                        "success": False,
                        "error": err_msg
                    }
        except Exception as e:
            err_msg = f"Jira API request exception: {str(e)}"
            logger.error(err_msg)
            return {
                "success": False,
                "error": err_msg
            }

jira_service = JiraService()
