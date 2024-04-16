import requests
import os
<<<<<<< HEAD
import jwt
from datetime import datetime, timedelta
from google.cloud import secretmanager
=======
import hashlib
import json
import jwt
from graphqlclient import GraphQLClient
from datetime import datetime, timedelta
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26


def message_building(conf, github_token):
    pr_info_text = ""
    pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    pr_info_text += f"*Reviewers*:\n{conf.pr_mentions}\n\n"
    pr_info_text += "*Files:*\n"
    pr_files = get_pr_files(conf, github_token)

    # Construct clickable links for each file
    for file_path in pr_files:
        print(f"testing {pr_files}")
        file_content_url = get_file_content_url(conf, file_path, github_token)
        if file_content_url:
            filename = os.path.basename(file_path)
            pr_info_text += f"<{file_content_url}|{filename}>\n"

    return pr_info_text


<<<<<<< HEAD
def github_api_request(github_token, endpoint):
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.get(endpoint, headers=headers)
=======
def github_api_request(conf, github_token, endpoint):
    url = f"https://api.github.com/repos/{conf.org}/{endpoint}"
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(url, headers=headers)
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch {endpoint}:", response.status_code)
        return None


<<<<<<< HEAD
def get_pr_files(conf, github_token):
    # Use the GitHub API to get the list of files in the pull request
    files_data = github_api_request(
        github_token, f"https://api.github.com/repos/{conf.org}/{conf.repo}/pulls/{conf.pr_number}/files"
    )
    print(f"pr file response: {files_data}")
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
        for file in files_data:
            if file["filename"] == file_path:
                diff_url = f"{conf.pr_url}/files#diff-{file['sha']}"
                print(f"diff url: {diff_url}")
                return diff_url
        print(f"File {file_path} not found in pull request {conf.pr_number}")
    else:
        print(f"Failed to fetch files for pull request {conf.pr_number}.")
    return None

def get_commit_messages(org, repo, pr_number, github_token):
    commits = github_api_request(github_token, f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/commits")
    print(f"commits: {commits}")
=======
def get_github_token():
    URL = f"https://api.github.com/app/installations/{os.environ.get('GH_APP_INSTALL_ID')}/access_tokens"
    issued_at = datetime.utcnow()
    duration = timedelta(minutes=10)
    payload = {
        'iat': issued_at,
        'exp': issued_at + duration,
        'iss': os.environ.get("GITHUB_APP_ID"),
    }
    with open(os.environ.get("GITHUB_JWT_PEM_KEY"), 'rb') as f:
        private_key = f.read()
    jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.post(URL, headers=headers)
    access_token = response.json()['token']
    
    return access_token

def get_commit_messages(conf, github_token):
    commits = github_api_request(conf, github_token, f"/{conf.repo}/pulls/{conf.pr_number}/commits")
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26
    if commits:
        if isinstance(commits, list):
            commit_messages = [commit["commit"]["message"] for commit in commits]
            print(f"commit messages: {commit_messages}")
        return commit_messages
    else:
        return None


<<<<<<< HEAD
def get_pr_checks(org, repo, github_token, commit_sha):
    checks = github_api_request(
        github_token, f"https://api.github.com/repos/{org}/{repo}/commits/{commit_sha}/check-runs"
=======
def get_pr_checks(conf, github_token):
    checks = github_api_request(
        conf, github_token, f"/{conf.repo}/commits/{conf.merge_commit_sha}/check-runs"
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26
    )
    print(f"checks result: {checks}")
    if checks:
        return checks
    else:
        return []


<<<<<<< HEAD
def get_team_members(org, team_slug, github_token):
    team_members = github_api_request(
        github_token, f"https://api.github.com/orgs/{org}/teams/{team_slug}/members"
=======
def get_team_members(conf, github_token):
    team_members = github_api_request(
        conf, github_token, f"/{conf.org}/teams/{conf.team_slug}/members"
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26
    )
    print(f"team members: {team_members}")
    if team_members:
        return sorted([member["login"] for member in team_members], key=str.lower)
    else:
        return None

<<<<<<< HEAD
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
    print("We got a GitHub token...")
    return access_token
=======

async def get_pr_files(conf, github_token):
    client = GraphQLClient("https://api.github.com/graphql")
    client.inject_token(github_token)

    files = []
    end_cursor = None

    while True:
        graphql_query = """
        query ($owner: String!, $repo: String!, $pull_request: Int!, $endCursor: String) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $pull_request) {
              files(first: 100, after: $endCursor) {
                totalCount
                pageInfo { endCursor hasNextPage }
                nodes { path }
              }
            }
          }
        }
        """
        variables = {
            "owner": conf.org,
            "repo": conf.repo,
            "pull_request": conf.pr_number,
            "endCursor": end_cursor,
        }
        response = await client.execute_async(query=graphql_query, variables=variables)
        data = json.loads(response)

        if (
            "data" in data
            and "repository" in data["data"]
            and "pullRequest" in data["data"]["repository"]
        ):
            pull_request = data["data"]["repository"]["pullRequest"]
            if "files" in pull_request:
                files += [file["path"] for file in pull_request["files"]["nodes"]]
                page_info = pull_request["files"]["pageInfo"]
                end_cursor = page_info["endCursor"]
                if not page_info["hasNextPage"]:
                    break
            else:
                break
        else:
            break

    return files
>>>>>>> 450fa8d7265af9a1c30d31c791395abdd8964b26
