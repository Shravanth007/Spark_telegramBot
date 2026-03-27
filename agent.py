import os
import json
import requests
from collections import defaultdict

from tools.github_tool import (
    create_issue, list_issues, list_prs, list_repos, create_repo, get_repo,
    list_branches, list_commits, get_issue, close_issue, comment_on_issue,
    reopen_issue, label_issue, delete_repo, star_repo, unstar_repo,
    create_pr, merge_pr, search_repos, fork_repo, get_pr, close_pr,
    list_collaborators, add_collaborator, get_user, list_releases,
)
from tools.gmail_tool import (
    read_emails, send_email, search_emails, get_email, reply_to_email,
    trash_email, mark_as_read, mark_as_unread, star_email, unstar_email,
    list_labels, email_stats, forward_email, archive_email, untrash_email,
    list_drafts, create_draft,
)
from tools.web_tool import web_search, fetch_url
from tools.notes_tool import save_note, get_note, list_notes, delete_note

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GITHUB_DEFAULT_USER = os.environ.get("GITHUB_DEFAULT_USER", "")

MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 5

_chat_history = defaultdict(list)

SYSTEM_PROMPT = f"""You are a personal AI assistant on Telegram. You have access to GitHub, Gmail, web search, and notes tools.

Personality:
- You are friendly, helpful, and concise
- This is a Telegram chat — keep responses short and to the point
- Vary your greetings naturally instead of always saying the same thing

Rules:
- Use the right tool for the job
- You can call multiple tools in sequence if the user asks for multiple things
- If a required parameter is missing, ask the user for it instead of guessing
- If no tool is needed, just chat normally
- Never make up data — only report real results from tools
- Always call the appropriate tool to get fresh data. Never answer questions about repos, issues, emails, etc. from memory

Smart Formatting — when creating or sending content through tools, compose it properly:

Email (gmail_send, gmail_reply, gmail_create_draft, gmail_forward):
- Write a professional, well-structured email with proper greeting and sign-off
- Match tone to context: formal for work, casual for friends
- If the user says "send email to X about Y", YOU write the full email body

GitHub Issues (github_create_issue):
- Write a clear, descriptive title and structured body

GitHub PRs (github_create_pr):
- Write a concise title and summary of changes

Confirmation for important actions:
- Before sending an email, show the user a preview and ask "Shall I send this?"
- Before deleting a repo (github_delete_repo), ALWAYS ask for confirmation first
- For other actions (creating issues, notes, etc.), just do it

GitHub context:
- The user's GitHub username is "{GITHUB_DEFAULT_USER}". If the user mentions just a repo name (e.g. "my-project"), prepend the username to make "{GITHUB_DEFAULT_USER}/my-project". If they give a full owner/repo, use that as-is. Always ask if you're unsure which repo they mean."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "github_create_issue",
            "description": "Create a new issue in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the issue"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body/description of the issue"
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_issues",
            "description": "List open issues in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_prs",
            "description": "List open pull requests in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_repos",
            "description": "List repositories for a GitHub user",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "GitHub username (defaults to GITHUB_DEFAULT_USER)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_repo",
            "description": "Create a new GitHub repository under the authenticated user's account",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the repository (e.g. 'my-new-project')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description of the repository"
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Whether the repository should be private (default: false = public)"
                    },
                    "auto_init": {
                        "type": "boolean",
                        "description": "Initialize with a README file (default: true)"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_repo",
            "description": "Get details about a specific GitHub repository (description, stars, forks, language, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_branches",
            "description": "List branches in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_commits",
            "description": "List recent commits in a GitHub repository, optionally on a specific branch",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: repo's default branch)"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_issue",
            "description": "Get details of a specific issue by number (title, body, state, labels, comments count)",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number"
                    }
                },
                "required": ["repo", "issue_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_close_issue",
            "description": "Close an open issue in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to close"
                    }
                },
                "required": ["repo", "issue_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_comment_on_issue",
            "description": "Add a comment to an issue in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to comment on"
                    },
                    "body": {
                        "type": "string",
                        "description": "The comment text"
                    }
                },
                "required": ["repo", "issue_number", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_reopen_issue",
            "description": "Reopen a closed issue in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to reopen"
                    }
                },
                "required": ["repo", "issue_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_label_issue",
            "description": "Add labels to an issue in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "The issue number to label"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of label names to add (e.g. ['bug', 'urgent'])"
                    }
                },
                "required": ["repo", "issue_number", "labels"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_delete_repo",
            "description": "Delete a GitHub repository. This is irreversible — always confirm with the user before calling this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_star_repo",
            "description": "Star a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_unstar_repo",
            "description": "Remove star from a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_pr",
            "description": "Create a pull request in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the pull request"
                    },
                    "head": {
                        "type": "string",
                        "description": "The branch that contains the changes (source branch)"
                    },
                    "base": {
                        "type": "string",
                        "description": "The branch to merge into (default: main)"
                    },
                    "body": {
                        "type": "string",
                        "description": "Description of the pull request"
                    }
                },
                "required": ["repo", "title", "head"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_merge_pr",
            "description": "Merge a pull request in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "The pull request number to merge"
                    },
                    "merge_method": {
                        "type": "string",
                        "description": "Merge method: 'merge', 'squash', or 'rebase' (default: merge)"
                    }
                },
                "required": ["repo", "pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_search_repos",
            "description": "Search for repositories across all of GitHub by keyword",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'machine learning python', 'language:go stars:>1000')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_fork_repo",
            "description": "Fork a repository to the authenticated user's account",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'facebook/react')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_pr",
            "description": "Get details of a specific pull request by number",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "The pull request number"
                    }
                },
                "required": ["repo", "pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_close_pr",
            "description": "Close a pull request without merging",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "The pull request number to close"
                    }
                },
                "required": ["repo", "pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_collaborators",
            "description": "List collaborators of a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_add_collaborator",
            "description": "Add a collaborator to a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    },
                    "username": {
                        "type": "string",
                        "description": "GitHub username to add as collaborator"
                    },
                    "permission": {
                        "type": "string",
                        "description": "Permission level: 'pull' (read), 'push' (write), or 'admin' (default: push)"
                    }
                },
                "required": ["repo", "username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_user",
            "description": "Get information about a GitHub user (bio, repos, followers, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "GitHub username"
                    }
                },
                "required": ["username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_releases",
            "description": "List releases of a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in owner/name format (e.g. 'username/myrepo')"
                    }
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_read",
            "description": "Read the last N emails from the user's inbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of recent emails to read (default: 5)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email on behalf of the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": "Search the user's emails by keyword or query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g. 'from:alice subject:invoice', 'is:unread', 'newer_than:1d')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_get_email",
            "description": "Get the full content/body of a specific email by its message ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID (returned by gmail_read or gmail_search)"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_reply",
            "description": "Reply to a specific email by its message ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to reply to"
                    },
                    "body": {
                        "type": "string",
                        "description": "The reply text"
                    }
                },
                "required": ["message_id", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_trash",
            "description": "Move an email to trash",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to trash"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_mark_read",
            "description": "Mark an email as read",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to mark as read"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_mark_unread",
            "description": "Mark an email as unread",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to mark as unread"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_star",
            "description": "Star an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to star"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_unstar",
            "description": "Remove star from an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to unstar"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_list_labels",
            "description": "List all Gmail labels (inbox, sent, custom labels, etc.)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_stats",
            "description": "Get email statistics: unread count, today's emails, starred count, sent today, inbox total",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_forward",
            "description": "Forward an email to another recipient",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to forward"
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email address to forward to"
                    }
                },
                "required": ["message_id", "to"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_archive",
            "description": "Archive an email (remove from inbox but keep it)",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to archive"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_untrash",
            "description": "Recover an email from trash",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to recover from trash"
                    }
                },
                "required": ["message_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_list_drafts",
            "description": "List all draft emails",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_create_draft",
            "description": "Create a draft email without sending it",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet using DuckDuckGo. Use this for any question about current events, facts, prices, news, weather, or anything the user wants to look up online.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g. 'latest iPhone price', 'who won the match today')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch_url",
            "description": "Fetch and extract text content from a webpage URL. Use this to read articles, blog posts, or any web page the user shares.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch (e.g. 'https://example.com/article')"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notes_save",
            "description": "Save a personal note with a title and content",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title for the note"
                    },
                    "content": {
                        "type": "string",
                        "description": "The note content"
                    }
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notes_get",
            "description": "Retrieve a specific saved note by title",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the note to retrieve"
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notes_list",
            "description": "List all saved notes",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notes_delete",
            "description": "Delete a saved note by title",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the note to delete"
                    }
                },
                "required": ["title"]
            }
        }
    }
]

TOOL_DISPATCH = {
    "github_create_issue": lambda args: create_issue(
        args.get("repo", ""), args.get("title", ""), args.get("body", "")
    ),
    "github_list_issues": lambda args: list_issues(args.get("repo", "")),
    "github_list_prs": lambda args: list_prs(args.get("repo", "")),
    "github_list_repos": lambda args: list_repos(args.get("username", "")),
    "github_create_repo": lambda args: create_repo(
        args.get("name", ""), args.get("description", ""),
        args.get("private", False), args.get("auto_init", True)
    ),
    "github_get_repo": lambda args: get_repo(args.get("repo", "")),
    "github_list_branches": lambda args: list_branches(args.get("repo", "")),
    "github_list_commits": lambda args: list_commits(
        args.get("repo", ""), args.get("branch", "")
    ),
    "github_get_issue": lambda args: get_issue(
        args.get("repo", ""), args.get("issue_number", 0)
    ),
    "github_close_issue": lambda args: close_issue(
        args.get("repo", ""), args.get("issue_number", 0)
    ),
    "github_comment_on_issue": lambda args: comment_on_issue(
        args.get("repo", ""), args.get("issue_number", 0), args.get("body", "")
    ),
    "github_reopen_issue": lambda args: reopen_issue(
        args.get("repo", ""), args.get("issue_number", 0)
    ),
    "github_label_issue": lambda args: label_issue(
        args.get("repo", ""), args.get("issue_number", 0), args.get("labels", [])
    ),
    "github_delete_repo": lambda args: delete_repo(args.get("repo", "")),
    "github_star_repo": lambda args: star_repo(args.get("repo", "")),
    "github_unstar_repo": lambda args: unstar_repo(args.get("repo", "")),
    "github_create_pr": lambda args: create_pr(
        args.get("repo", ""), args.get("title", ""), args.get("head", ""),
        args.get("base", "main"), args.get("body", "")
    ),
    "github_merge_pr": lambda args: merge_pr(
        args.get("repo", ""), args.get("pr_number", 0), args.get("merge_method", "merge")
    ),
    "github_search_repos": lambda args: search_repos(args.get("query", "")),
    "github_fork_repo": lambda args: fork_repo(args.get("repo", "")),
    "github_get_pr": lambda args: get_pr(
        args.get("repo", ""), args.get("pr_number", 0)
    ),
    "github_close_pr": lambda args: close_pr(
        args.get("repo", ""), args.get("pr_number", 0)
    ),
    "github_list_collaborators": lambda args: list_collaborators(args.get("repo", "")),
    "github_add_collaborator": lambda args: add_collaborator(
        args.get("repo", ""), args.get("username", ""), args.get("permission", "push")
    ),
    "github_get_user": lambda args: get_user(args.get("username", "")),
    "github_list_releases": lambda args: list_releases(args.get("repo", "")),
    "gmail_read": lambda args: read_emails(args.get("count", 5)),
    "gmail_send": lambda args: send_email(
        args.get("to", ""), args.get("subject", ""), args.get("body", "")
    ),
    "gmail_search": lambda args: search_emails(args.get("query", "")),
    "gmail_get_email": lambda args: get_email(args.get("message_id", "")),
    "gmail_reply": lambda args: reply_to_email(
        args.get("message_id", ""), args.get("body", "")
    ),
    "gmail_trash": lambda args: trash_email(args.get("message_id", "")),
    "gmail_mark_read": lambda args: mark_as_read(args.get("message_id", "")),
    "gmail_mark_unread": lambda args: mark_as_unread(args.get("message_id", "")),
    "gmail_star": lambda args: star_email(args.get("message_id", "")),
    "gmail_unstar": lambda args: unstar_email(args.get("message_id", "")),
    "gmail_list_labels": lambda args: list_labels(),
    "gmail_stats": lambda args: email_stats(),
    "gmail_forward": lambda args: forward_email(
        args.get("message_id", ""), args.get("to", "")
    ),
    "gmail_archive": lambda args: archive_email(args.get("message_id", "")),
    "gmail_untrash": lambda args: untrash_email(args.get("message_id", "")),
    "gmail_list_drafts": lambda args: list_drafts(),
    "gmail_create_draft": lambda args: create_draft(
        args.get("to", ""), args.get("subject", ""), args.get("body", "")
    ),
    "web_search": lambda args: web_search(args.get("query", "")),
    "web_fetch_url": lambda args: fetch_url(args.get("url", "")),
    "notes_save": lambda args: save_note(args.get("title", ""), args.get("content", "")),
    "notes_get": lambda args: get_note(args.get("title", "")),
    "notes_list": lambda args: list_notes(),
    "notes_delete": lambda args: delete_note(args.get("title", "")),
}


def _call_llm(messages, tools=None):
    if not OPENROUTER_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    for model in MODELS:
        payload = {
            "model": model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if r.status_code == 429 or r.status_code == 404:
            continue
        r.raise_for_status()
        return r.json()

    return None


_ROUTE_KEYWORDS = {
    "github": [
        "repo", "repos", "repository", "github", "git", "issue", "issues",
        "pr", "pull request", "branch", "branches", "commit", "commits",
        "fork", "star repo", "unstar repo", "collaborator", "release",
        "merge", "label", "reopen",
    ],
    "gmail": [
        "email", "emails", "mail", "mails", "inbox", "send", "reply",
        "forward", "draft", "drafts", "unread", "archive", "trash",
        "untrash", "starred email", "gmail", "label",
    ],
    "web": [
        "search", "look up", "lookup", "find online", "google", "website",
        "url", "article", "summarize", "news", "weather", "price", "who is",
        "what is", "when is", "where is", "how to", "latest", "current",
        "today", "http://", "https://",
    ],
    "notes": [
        "note", "notes", "save note", "my notes", "remember this",
        "memo", "delete note", "show notes",
    ],
}

TOOLS_BY_CATEGORY = {}
for _tool in TOOLS:
    _name = _tool["function"]["name"]
    _cat = _name.split("_")[0]
    TOOLS_BY_CATEGORY.setdefault(_cat, []).append(_tool)


def _route_tools(message):
    """
    Pick relevant tool categories based on message keywords.
    Returns a filtered tool list for the first LLM call.
    """
    msg = message.lower()
    matched = set()

    for category, keywords in _ROUTE_KEYWORDS.items():
        for kw in keywords:
            if kw in msg:
                matched.add(category)
                break

    if not matched:
        return TOOLS

    routed = []
    for cat in matched:
        routed.extend(TOOLS_BY_CATEGORY.get(cat, []))

    return routed if routed else TOOLS


def _execute_tool_calls(tool_calls):
    """Execute all tool calls from a single LLM response and return results."""
    results = []
    for tool_call in tool_calls:
        func_name = tool_call["function"]["name"]

        try:
            args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            args = {}

        executor = TOOL_DISPATCH.get(func_name)
        if not executor:
            result = {"success": False, "error": f"Unknown tool: {func_name}"}
        else:
            try:
                result = executor(args)
            except Exception as e:
                result = {"success": False, "error": f"Tool execution failed: {str(e)}"}

        results.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(result),
        })
    return results


def run_agent(user_message, chat_id=None):
    """
    Main agent loop.

    1. Builds the message list: system prompt + conversation history + new message.
    2. Routes to relevant tools based on keywords in the message.
    3. Calls the LLM. If it returns tool_calls, executes them and loops.
    4. When the LLM returns a plain text response, saves history and returns it.
    5. Caps at MAX_TOOL_ROUNDS to prevent infinite loops.
    """
    history = _chat_history[chat_id] if chat_id else []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": user_message},
    ]

    routed_tools = _route_tools(user_message)

    for _round in range(MAX_TOOL_ROUNDS):
        active_tools = routed_tools if _round == 0 else TOOLS
        try:
            data = _call_llm(messages, tools=active_tools)
        except Exception as e:
            return f"Sorry, I couldn't reach the AI service right now. Error: {str(e)}"

        if not data:
            return "OpenRouter API key is not configured."

        try:
            choice = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return "Received an unexpected response from the AI service."

        messages.append(choice)

        if not choice.get("tool_calls"):
            reply = choice.get("content", "I'm not sure how to help with that.")
            if chat_id is not None:
                _chat_history[chat_id].append({"role": "user", "content": user_message})
                _chat_history[chat_id].append({"role": "assistant", "content": reply})
                if len(_chat_history[chat_id]) > MAX_HISTORY:
                    _chat_history[chat_id] = _chat_history[chat_id][-MAX_HISTORY:]
            return reply

        tool_results = _execute_tool_calls(choice["tool_calls"])
        messages.extend(tool_results)

    return "I hit my tool limit for this request. Please try again with a simpler request."

