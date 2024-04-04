import requests
import os
import hashlib
import json
from graphqlclient import GraphQLClient


def message_building(conf):
    pr_info_text = ""
    pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    pr_info_text += f"*Reviewers*:\n{conf.pr_mentions}\n\n"
    pr_info_text += "*Files:*\n"
    pr_files = get_pr_files(conf)

    # Construct clickable links for each file
    for file_path in pr_files:
        with open(file_path, "rb") as file:
            file_content = file.read()
            sha256_hash = hashlib.sha256(file_content).hexdigest()
        file_link = f"https://github.com/{conf.org}/{conf.repo}/pull/{conf.pr_number}/files#diff-{sha256_hash}"
        filename = os.path.basename(file_path)
        pr_info_text += f"<{file_link}|{filename}>\n"

    return pr_info_text

def github_api_request(conf, endpoint):
    url = f"https://api.github.com/repos/{conf.org}/{endpoint}"
    headers = {"Authorization": f"token {conf.github_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch {endpoint}:", response.status_code)
        return None

def get_commit_messages(conf):
    commits = github_api_request(conf, f"/{conf.repo}/pulls/{conf.pr_number}/commits")
    if commits:
        commit_messages = [commit['commit']['message'] for commit in commits]
        return commit_messages
    else:
        return None

def get_pr_checks(conf):
    checks = github_api_request(conf, f"/{conf.repo}/commits/{conf.merge_commit_sha}/check-runs")
    if checks:
        return checks
    else:
        return None

def get_team_members(conf):
    team_members = github_api_request(conf, f"/{conf.org}/teams/{conf.team_slug}/members")
    if team_members:
        return team_members
    else:
        return None

async def get_pr_files(conf):
    client = GraphQLClient("https://api.github.com/graphql")
    client.inject_token(conf.github_token)
    
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
            "endCursor": end_cursor
        }
        response = await client.execute_async(query=graphql_query, variables=variables)
        data = json.loads(response)
        
        if "data" in data and "repository" in data["data"] and "pullRequest" in data["data"]["repository"]:
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
