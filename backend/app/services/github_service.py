import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger("meetme.services.github")

class GitHubService:
    """
    Real GitHub Issues REST API integration.
    Authenticates with Personal Access Token (PAT) over HTTPS Port 443.
    """

    async def test_connection(self, token: str, repo: str) -> Dict[str, Any]:
        """
        Validates GitHub authentication and repository access (e.g., 'owner/repo').
        """
        clean_repo = repo.replace("https://github.com/", "").strip("/")
        url = f"https://api.github.com/repos/{clean_repo}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MEETME-Autonomous-Platform"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    full_name = data.get("full_name", clean_repo)
                    description = data.get("description", "")
                    return {
                        "success": True,
                        "repo": full_name,
                        "description": description,
                        "message": f"Successfully connected to GitHub repository: {full_name}."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"GitHub authentication failed ({resp.status_code}): {resp.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"GitHub connection error: {str(e)}"
            }

    async def create_issue(
        self,
        token: str,
        repo: str,
        title: str,
        description: str,
        priority: str = "MEDIUM",
        deadline: Optional[str] = None,
        evidence: Optional[str] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates an actual GitHub issue in the specified repository from an approved MEETME task.
        """
        clean_repo = repo.replace("https://github.com/", "").strip("/")
        url = f"https://api.github.com/repos/{clean_repo}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MEETME-Autonomous-Platform"
        }

        # Format markdown body
        body_lines = [
            f"### Action Item Description",
            f"{description or title}\n",
            f"| Attribute | Value |",
            f"| :--- | :--- |",
            f"| **Priority** | `{priority}` |",
            f"| **Deadline** | `{deadline or 'Not specified'}` |",
            f"| **Evidence Quote** | *\"{evidence or 'Extracted during meeting'}\"* |",
            f"\n> 🤖 *Created and approved autonomously via [MEETME Platform](https://meetme-lake.vercel.app)*"
        ]
        body = "\n".join(body_lines)

        labels = ["meetme", f"priority:{priority.lower()}"]
        payload: Dict[str, Any] = {
            "title": title[:255],
            "body": body,
            "labels": labels
        }
        if assignees:
            payload["assignees"] = assignees

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    issue_number = data.get("number")
                    issue_id = str(data.get("id"))
                    issue_url = data.get("html_url")
                    logger.info(f"Created GitHub issue #{issue_number} in {clean_repo}: {issue_url}")
                    return {
                        "success": True,
                        "issue_number": issue_number,
                        "issue_id": issue_id,
                        "issue_url": issue_url,
                        "provider": "GITHUB"
                    }
                else:
                    err_msg = f"Failed to create GitHub issue ({resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    return {
                        "success": False,
                        "error": err_msg
                    }
        except Exception as e:
            err_msg = f"GitHub API request exception: {str(e)}"
            logger.error(err_msg)
            return {
                "success": False,
                "error": err_msg
            }

github_service = GitHubService()
