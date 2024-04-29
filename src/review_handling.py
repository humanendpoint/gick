import os
import requests
import github_tools
import json
from slack_sdk import WebClient


def decision_handling(actions, user):
    decision = actions[0]["value"]
    decision_message = ""
    message = github_decision(decision, actions, user)
    if decision == "REQUEST_CHANGES":
        decision_message = ":warning: " + message + f" by <@{user}>!"
    elif decision == "MERGE":
        decision_message = ":tada: " + message + f" (by <@{user}>)"
    elif decision == "SQUASH":
        decision_message = ":red-cross-mark: Squashed!"

    return decision, decision_message


def github_decision(decision, actions, assignee):
    action_id = actions[0]["action_id"]
    pull_request_id = action_id.split("-")[0]
    github_token = github_tools.get_github_token()
    s_token = os.environ.get("SLACK_TOKEN")
    client = WebClient(token=s_token)
    re = client.users_profile_get(user=assignee)
    print(f"user profile response: {re}")
    decider = re["profile"]["real_name"]
    org = os.environ.get("ORG")
    repo = os.environ.get("REPO")
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if decision == "APPROVE":
        data = {"event": decision, "body": f"approved from Slack by {decider}"}
        data = json.dumps(data)
        url = (
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pull_request_id}/reviews"
        )
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            message = (
                "Approved"
                if response.json().get("state", "") == "APPROVED"
                else "Request Changes"
            )
            return message
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while making the request: {e}")
            return "Error approving the pull request"
    elif decision == "MERGE":
        decision = decision.lower()
        data = {"merge_method": f"{decision}"}
        data = json.dumps(data)
        merge_url = (
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pull_request_id}/merge"
        )
        try:
            response = requests.put(
                merge_url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            print(f"GitHub API response for merged decision: {response.text}")
            return response.json().get("message", "")
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while making the request: {e}")
            return "Error merging the pull request"
