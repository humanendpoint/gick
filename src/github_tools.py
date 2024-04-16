import requests
import os
import jwt
from datetime import datetime, timedelta
from google.cloud import secretmanager


def message_building(conf, github_token):
    pr_info_text = ""
    pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    pr_info_text += f"*Reviewers*:\n{conf.pr_mentions}\n<\n"
    pr_info_text += "*Files:*\n"
    pr_files = get_pr_files(conf, github_token)

    # Construct clickable links for each file
    for file_path in pr_files:
        file_content_url = get_file_content_url(conf, file_path, github_token)
        if file_content_url:
            filename = os.path.basename(file_path)
            pr_info_text += f"<{file_content_url}|{filename}>\n"

    return pr_info_text


def github_api_request(github_token, endpoint):
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch {endpoint}:", response.status_code)
        return None


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

def get_file_content_url(conf, file_path, github_token):
    files_data = github_api_request(
        github_token, f"https://api.github.com/repos/{conf.org}/{conf.repo}/pulls/{conf.pr_number}/files"
    )
    if files_data:
        for file_data in files_data:
            if file_data["filename"] == file_path:
                diff_url = f"{conf.pr_url}/files#diff-{file_data['sha']}"
                return diff_url
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
    # Use the PEM content directly as the key to sign the JWT
    jwt_token = jwt.encode(payload, pem, algorithm='RS256')
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.post(URL, headers=headers)
    access_token = response.json()['token']
    print("Got a GitHub token.")
    return access_token
