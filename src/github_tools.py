import requests
import os
import jwt
import hashlib
from datetime import datetime, timedelta
from google.cloud import secretmanager
import github_tools


def github_api_request(github_token, endpoint):
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch {endpoint}:", response.status_code)
        return None


#def add_comment_on_merge(merger):
#    org = os.environ.get("ORG")
#    repo = os.environ.get("REPO")
#    submission = f"Merged by {merger}"
#    submission_with_commenter = f"{submission}<br><br><br><sub>Comment added by gick-app</sub>"
#    github_token = github_tools.get_github_token()
#    github_comment_url = (
#        f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/reviews"
#    )
#    headers = {
#        "Authorization": f"Bearer {github_token}", 
#        "Accept": "application/vnd.github+json", 
#        "X-GitHub-Api-Version": "2022-11-28"
#    }
#    data = {"body": submission_with_commenter, "event": "COMMENT"}
#    response = requests.post(github_comment_url, headers=headers, json=data)
#
#    return response

def get_pr_files(conf, github_token):
    # Use the GitHub API to get the list of files in the pull request
    files_data = github_api_request(
        github_token, f"https://api.github.com/repos/{conf.org}/{conf.repo}/pulls/{conf.pr_number}/files"
    )
    if files_data:
        pr_files = [file_data["filename"] for file_data in files_data]
        return pr_files
    else:
        print(f"Failed to fetch files for pull request {conf.pr_number}")
        return []

def get_diff_content(url, github_token):
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.diff",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch diff content from {url}")
        return None

def get_file_content_url(conf, file_path, github_token):
    files_data = github_api_request(
        github_token, f"https://api.github.com/repos/{conf.org}/{conf.repo}/pulls/{conf.pr_number}/files"
    )
    if files_data:
        for file_data in files_data:
            try:
                print(f"file data name: {file_data['filename']}")
                print(f"the file_path: {file_path}")
                if file_data["filename"] == file_path:
                    file_path_bytes = file_path.encode('utf-8')
                    file_sha = hashlib.sha256(file_path_bytes).hexdigest()
                    diff_url = f"https://github.com/{conf.org}/{conf.repo}/pull/{conf.pr_number}/files#diff-{file_sha}"
                    return diff_url
            except Exception as error:
                print(f"calculating file hash error: {error}")
        print(f"File {file_path} not found in pull request {conf.pr_number}")
    else:
        print(f"Failed to fetch files for pull request {conf.pr_number}.")
    return None

def get_commit_messages(org, repo, pr_number, github_token):
    commits = github_api_request(github_token, f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/commits")
    if commits:
        if isinstance(commits, list):
            commit_messages = [commit["commit"]["message"] for commit in commits]
        return commit_messages
    else:
        return None


def get_pr_checks(org, repo, github_token, commit_sha):
    checks = github_api_request(
        github_token, f"https://api.github.com/repos/{org}/{repo}/commits/{commit_sha}/check-runs"
    )
    if checks:
        return checks
    else:
        return []


def get_team_members(org, team_slug, github_token):
    team_members = github_api_request(
        github_token, f"https://api.github.com/orgs/{org}/teams/{team_slug}/members"
    )
    if team_members:
        return sorted([member["login"] for member in team_members], key=str.lower)
    else:
        return None

def get_github_token():
    URL = f"https://api.github.com/app/installations/{os.environ.get('GH_APP_INSTALL_ID')}/access_tokens"
    client = secretmanager.SecretManagerServiceClient()
    key_name = os.environ.get("GITHUB_JWT_KEYNAME")
    # Retrieve secret from Secret Manager
    secret_name = "projects/{}/secrets/{}/versions/latest".format(os.environ.get("PROJECT_ID"), key_name)
    response = client.access_secret_version(name=secret_name)
    pem = response.payload.data.decode("UTF-8")
    issued_at = datetime.utcnow()
    duration = timedelta(minutes=10)
    payload = {
        'iat': issued_at,
        'exp': issued_at + duration,
        'iss': os.environ.get("GITHUB_APP_ID"),
    }
    jwt_token = jwt.encode(payload, pem, algorithm='RS256')
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.post(URL, headers=headers)
    access_token = response.json()['token']
    print("Got a GitHub token.")
    return access_token
