import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_DEFAULT_REPO = os.environ.get("GITHUB_DEFAULT_REPO", "")
GITHUB_DEFAULT_USER = os.environ.get("GITHUB_DEFAULT_USER", "")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_URL = "https://api.github.com"


def _error_msg(r):
    try:
        return r.json().get("message", f"HTTP {r.status_code}")
    except (ValueError, KeyError):
        return f"HTTP {r.status_code}"


def _check_repo(repo):
    repo = repo or GITHUB_DEFAULT_REPO
    if not repo:
        return None, {"success": False, "error": "No repo specified."}
    if not GITHUB_TOKEN:
        return None, {"success": False, "error": "GitHub token not configured."}
    return repo, None


def create_issue(repo, title, body=""):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues"
        data = {"title": title, "body": body}
        r = requests.post(url, json=data, headers=HEADERS, timeout=15)

        if r.status_code == 201:
            issue = r.json()
            return {
                "success": True,
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_issues(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues"
        r = requests.get(url, headers=HEADERS, params={"state": "open", "per_page": 10}, timeout=15)

        if r.status_code == 200:
            issues = [i for i in r.json() if "pull_request" not in i]
            return {
                "success": True,
                "count": len(issues),
                "issues": [
                    {"number": i["number"], "title": i["title"], "url": i["html_url"]}
                    for i in issues
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_prs(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/pulls"
        r = requests.get(url, headers=HEADERS, params={"state": "open", "per_page": 10}, timeout=15)

        if r.status_code == 200:
            prs = r.json()
            return {
                "success": True,
                "count": len(prs),
                "prs": [
                    {"number": p["number"], "title": p["title"], "url": p["html_url"]}
                    for p in prs
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_repos(username=""):
    if not GITHUB_TOKEN:
        return {"success": False, "error": "GitHub token not configured."}

    try:
        if not username or username == GITHUB_DEFAULT_USER:
            url = f"{BASE_URL}/user/repos"
            params = {"sort": "updated", "per_page": 20, "affiliation": "owner"}
        else:
            url = f"{BASE_URL}/users/{username}/repos"
            params = {"sort": "updated", "per_page": 20}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)

        if r.status_code == 200:
            repos = r.json()
            return {
                "success": True,
                "count": len(repos),
                "repos": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "private": repo.get("private", False),
                        "url": repo["html_url"],
                    }
                    for repo in repos
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def create_repo(name, description="", private=False, auto_init=True):
    if not name:
        return {"success": False, "error": "Repository name is required."}
    if not GITHUB_TOKEN:
        return {"success": False, "error": "GitHub token not configured."}

    try:
        url = f"{BASE_URL}/user/repos"
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        r = requests.post(url, json=data, headers=HEADERS, timeout=15)

        if r.status_code == 201:
            repo = r.json()
            return {
                "success": True,
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description", ""),
                "private": repo.get("private", False),
                "url": repo["html_url"],
                "clone_url": repo["clone_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def get_repo(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "name": data["name"],
                "full_name": data["full_name"],
                "description": data.get("description", ""),
                "language": data.get("language", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "default_branch": data.get("default_branch", "main"),
                "private": data.get("private", False),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "url": data["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_branches(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/branches"
        r = requests.get(url, headers=HEADERS, params={"per_page": 20}, timeout=15)

        if r.status_code == 200:
            branches = r.json()
            return {
                "success": True,
                "count": len(branches),
                "branches": [
                    {"name": b["name"], "protected": b.get("protected", False)}
                    for b in branches
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_commits(repo, branch=""):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/commits"
        params = {"per_page": 10}
        if branch:
            params["sha"] = branch
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)

        if r.status_code == 200:
            commits = r.json()
            return {
                "success": True,
                "count": len(commits),
                "commits": [
                    {
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].split("\n")[0],
                        "author": c["commit"]["author"]["name"],
                        "date": c["commit"]["author"]["date"],
                        "url": c["html_url"],
                    }
                    for c in commits
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def get_issue(repo, issue_number):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues/{issue_number}"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            i = r.json()
            return {
                "success": True,
                "number": i["number"],
                "title": i["title"],
                "body": i.get("body", ""),
                "state": i["state"],
                "author": i["user"]["login"],
                "labels": [l["name"] for l in i.get("labels", [])],
                "comments": i.get("comments", 0),
                "created_at": i.get("created_at", ""),
                "url": i["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def close_issue(repo, issue_number):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues/{issue_number}"
        r = requests.patch(url, json={"state": "closed"}, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            i = r.json()
            return {
                "success": True,
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "url": i["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def comment_on_issue(repo, issue_number, body):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues/{issue_number}/comments"
        r = requests.post(url, json={"body": body}, headers=HEADERS, timeout=15)

        if r.status_code == 201:
            c = r.json()
            return {
                "success": True,
                "comment_id": c["id"],
                "url": c["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def reopen_issue(repo, issue_number):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues/{issue_number}"
        r = requests.patch(url, json={"state": "open"}, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            i = r.json()
            return {
                "success": True,
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "url": i["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def label_issue(repo, issue_number, labels):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/issues/{issue_number}/labels"
        r = requests.post(url, json={"labels": labels}, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            return {
                "success": True,
                "labels": [l["name"] for l in r.json()],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def delete_repo(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}"
        r = requests.delete(url, headers=HEADERS, timeout=15)

        if r.status_code == 204:
            return {"success": True, "repo": repo, "action": "deleted"}

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def star_repo(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/user/starred/{repo}"
        r = requests.put(url, headers={**HEADERS, "Content-Length": "0"}, timeout=15)

        if r.status_code == 204:
            return {"success": True, "repo": repo, "action": "starred"}

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def unstar_repo(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/user/starred/{repo}"
        r = requests.delete(url, headers=HEADERS, timeout=15)

        if r.status_code == 204:
            return {"success": True, "repo": repo, "action": "unstarred"}

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def create_pr(repo, title, head, base="main", body=""):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/pulls"
        data = {"title": title, "head": head, "base": base, "body": body}
        r = requests.post(url, json=data, headers=HEADERS, timeout=15)

        if r.status_code == 201:
            pr = r.json()
            return {
                "success": True,
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def merge_pr(repo, pr_number, merge_method="merge"):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/pulls/{pr_number}/merge"
        data = {"merge_method": merge_method}
        r = requests.put(url, json=data, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            result = r.json()
            return {
                "success": True,
                "merged": result.get("merged", False),
                "message": result.get("message", ""),
                "sha": result.get("sha", "")[:7],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def search_repos(query):
    if not GITHUB_TOKEN:
        return {"success": False, "error": "GitHub token not configured."}

    try:
        url = f"{BASE_URL}/search/repositories"
        r = requests.get(url, headers=HEADERS, params={"q": query, "per_page": 10}, timeout=15)

        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "count": data.get("total_count", 0),
                "repos": [
                    {
                        "full_name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "url": repo["html_url"],
                    }
                    for repo in data.get("items", [])
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def fork_repo(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/forks"
        r = requests.post(url, headers=HEADERS, timeout=15)

        if r.status_code == 202:
            fork = r.json()
            return {
                "success": True,
                "full_name": fork["full_name"],
                "url": fork["html_url"],
                "clone_url": fork["clone_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def get_pr(repo, pr_number):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/pulls/{pr_number}"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            pr = r.json()
            return {
                "success": True,
                "number": pr["number"],
                "title": pr["title"],
                "body": pr.get("body", ""),
                "state": pr["state"],
                "author": pr["user"]["login"],
                "head": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "mergeable": pr.get("mergeable"),
                "changed_files": pr.get("changed_files", 0),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "created_at": pr.get("created_at", ""),
                "url": pr["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def close_pr(repo, pr_number):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/pulls/{pr_number}"
        r = requests.patch(url, json={"state": "closed"}, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            pr = r.json()
            return {
                "success": True,
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "url": pr["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_collaborators(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/collaborators"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            collabs = r.json()
            return {
                "success": True,
                "count": len(collabs),
                "collaborators": [
                    {
                        "username": c["login"],
                        "role": c.get("role_name", ""),
                        "url": c["html_url"],
                    }
                    for c in collabs
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def add_collaborator(repo, username, permission="push"):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/collaborators/{username}"
        r = requests.put(url, json={"permission": permission}, headers=HEADERS, timeout=15)

        if r.status_code in (201, 204):
            return {"success": True, "username": username, "permission": permission, "repo": repo}

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def get_user(username):
    if not GITHUB_TOKEN:
        return {"success": False, "error": "GitHub token not configured."}

    try:
        url = f"{BASE_URL}/users/{username}"
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 200:
            u = r.json()
            return {
                "success": True,
                "username": u["login"],
                "name": u.get("name", ""),
                "bio": u.get("bio", ""),
                "public_repos": u.get("public_repos", 0),
                "followers": u.get("followers", 0),
                "following": u.get("following", 0),
                "company": u.get("company", ""),
                "location": u.get("location", ""),
                "url": u["html_url"],
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}


def list_releases(repo):
    repo, err = _check_repo(repo)
    if err:
        return err

    try:
        url = f"{BASE_URL}/repos/{repo}/releases"
        r = requests.get(url, headers=HEADERS, params={"per_page": 5}, timeout=15)

        if r.status_code == 200:
            releases = r.json()
            return {
                "success": True,
                "count": len(releases),
                "releases": [
                    {
                        "tag": rel["tag_name"],
                        "name": rel.get("name", ""),
                        "published_at": rel.get("published_at", ""),
                        "prerelease": rel.get("prerelease", False),
                        "url": rel["html_url"],
                    }
                    for rel in releases
                ]
            }

        return {"success": False, "error": _error_msg(r)}
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}

