import utilities, review_handling
import requests
import os

def decision_handling(actions, user):            
    decision = utilities.extract_value(actions[0], ["value"])
    decision_message = ""
    decision, message = review_handling.github_decision(decision, actions)
    if decision == "REQUEST_CHANGES":
        decision_message = ":warning:" + message + f"by <@{user}>!"
    elif decision == "MERGE":
        decision_message = ":tada:" + message + f"(by {user})"
    elif decision == "SQUASH":
        decision_message = ":red-cross-mark: Squashed!"
    
    return decision, decision_message

def github_decision(decision, actions):
    action_id = utilities.extract_value(actions[0], ["action_id"])
    pull_request_id = action_id[:-2]
    headers = {"Authorization": f"token {os.environ.get("GITHUB_TOKEN")}"}
    if decision == "APPROVE":
        data = {"event":f"{decision}"}
        response = requests.post(f"https://api.github.com/repos/{os.environ.get("ORG")}/{os.environ.get("REPO")}/pulls/{pull_request_id}/reviews", headers=headers, data=data)
        print(f"GitHub API response for approved decision: {response}")
        message = "Approved" if response.json().get("state", "") == "APPROVED" else "Changes requested"
        return message
    elif decision == "MERGE":
        decision.lower()
        data = {"merge_method":f"{decision}"}
        response = requests.post(f"https://api.github.com/repos/{os.environ.get("ORG")}/{os.environ.get("REPO")}/pulls/{pull_request_id}/merge", headers=headers, data=data)
        print(f"GitHub API response for merged decision: {response}")
        return response.json().get("message", "")
