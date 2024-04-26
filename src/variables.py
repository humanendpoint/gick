import os
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
import utilities, okta_tools

class vars:
    def __init__(self, client, payload, org, repo, github_token):
        self.org = org
        self.repo = repo
        self.channel_id = os.environ.get("CHANNEL_ID")
        self.team_slug = os.environ.get("GITHUB_TEAM_SLUG")
        self.okta_token = os.environ.get("OKTA_TOKEN")
        self.okta_url = os.environ.get("OKTA_URL")
        self.slack_token = os.environ.get("SLACK_TOKEN")
        self.webhook_secret_token = os.environ.get("GITHUB_WEBHOOK_SECRET")
        self.pr_user_login = payload.get("user", {}).get("login", "")
        self.pr_url = utilities.extract_value(payload, ["html_url"])
        self.pr_number = utilities.extract_value(payload, ["number"])
        self.pr_title = utilities.extract_value(payload, ["title"])
        self.pr_branch = utilities.extract_value(payload, ["head", "ref"])
        self.assignee_emails = self.get_assignee_emails() or okta_tools.get_okta_usernames(
            self.org, self.team_slug, self.okta_token, self.okta_url, payload, github_token
        )
        self.pr_mentions = self.get_slack_users(client)
        self.merge_commit_sha = utilities.extract_value(payload, ["head", "sha"])

    def get_assignee_emails(self):
        secret_value = os.environ.get("ASSIGNEE_EMAILS")
        if secret_value:
            return secret_value.strip().split()
        else:
            return None 

    def get_slack_users(self, client):
        mention_string = ""
        for email in self.assignee_emails:
            try:
                response = client.users_lookupByEmail(email=email)
                user_id = response["user"]["id"]
                mention_string += f" <@{user_id}>"
            except SlackApiError as e:
                print(f"Error tagging user with email {email}: {e.response['error']}")

        return mention_string


# load up class config
def get_variables(payload, repo, org, github_token):
    """Get confuration from environment variables."""
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    return vars(client, payload, org, repo, github_token)
