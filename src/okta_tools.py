import requests
import json
import utilities, github_tools


def get_okta_usernames(org, team_slug, okta_token, okta_url, payload):
    # github users
    team_users = github_tools.get_team_members(org, team_slug)
    # get okta suporg members
    response_data = get_okta_info(okta_token, okta_url)
    # sort the emails from okta
    sorted_emails = sorted(response_data["values"])
    # Extract sorted usernames
    usernames = team_users.split(",")
    sorted_usernames = sorted(usernames, key=str.lower)
    # Match usernames to email addresses based on similarity score
    username_email_map = {}
    for username in sorted_usernames:
        best_score = 0
        best_email = None
        for email in sorted_emails:
            score = utilities.similarity_score(username, email)
            if score > best_score:
                best_score = score
                best_email = email
        if best_email:
            username_email_map[username] = best_email

    # Extract assignees and match with emails using mapping dictionary
    assignees_output = utilities.extract_values(payload, ["assignees"])
    assignees = json.loads(assignees_output)["assignees"]
    login_list = [assignee["login"] for assignee in assignees]
    # Retrieve emails corresponding to assignees using mapping dictionary
    assignee_emails = [username_email_map.get(login) for login in login_list]

    return assignee_emails


def get_okta_info(okta_token, okta_url):
    headers = {
        "Authorization": f"SSWS {okta_token}",
        "content-type": "application/json",
    }
    response = requests.post(okta_url, headers=headers)
    response_data = response.json()
    return response_data
