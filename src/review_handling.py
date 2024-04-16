import os
import requests
import github_tools
import json


def decision_handling(actions, user):
    decision = actions[0]["value"]
    decision_message = ""
    message = github_decision(decision, actions)
    if decision == "REQUEST_CHANGES":
        decision_message = ":warning:" + message + f"by <@{user}>!"
    elif decision == "MERGE":
        decision_message = ":tada:" + message + f"(by {user})"
    elif decision == "SQUASH":
        decision_message = ":red-cross-mark: Squashed!"

    return decision, decision_message


def github_decision(decision, actions):
    action_id = actions[0]["action_id"]
    pull_request_id = action_id.split("-")[0]
    github_token = github_tools.get_github_token()
    org = os.environ.get('ORG')
    repo = os.environ.get('REPO')
    headers = {
        "Authorization": f"Bearer {github_token}", 
        "Accept": "application/vnd.github+json", 
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if decision == "APPROVE":
        data = {"event": decision}
        data = json.dumps(data)
        url = f"https://api.github.com/repos/{org}/{repo}/pulls/{pull_request_id}/reviews"
        response = requests.post(
            url,
            headers=headers,
            data=data,
        )
        message = (
            "Approved"
            if response.json().get("state", "") == "APPROVED"
            else "Request Changes"
        )
        return message
    elif decision == "MERGE":
        decision = decision.lower()
        data = {"merge_method": f"{decision}"}
        data = json.dumps(data)
        merge_url = f"https://api.github.com/repos/{org}/{repo}/pulls/{pull_request_id}/merge"
        response = requests.put(
            merge_url,
            headers=headers,
            json=data,
        )
        return response.json().get("message", "")
