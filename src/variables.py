import os
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
import utilities, okta_tools


class vars:
    def __init__(self, client, payload, org, repo):
        self.org = org
        self.repo = repo
        self.channel_id = os.environ.get("CHANNEL_ID")
        self.team_slug = os.environ.get("GITHUB_TEAM_SLUG")
        self.okta_token = os.environ.get("OKTA_TOKEN")
        self.okta_url = os.environ.get("OKTA_URL")
        self.slack_token = os.environ.get("SLACK_TOKEN")
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.webhook_secret_token = os.environ.get("GITHUB_WEBHOOK_SECRET")
        self.pr_user_login = utilities.extract_value(payload, ["assignees"][0]["name"])
        self.pr_url = utilities.extract_value(payload, ["url"])
        self.pr_number = utilities.extract_value(payload, ["number"])
        self.pr_title = utilities.extract_value(payload, ["title"])
        self.pr_branch = utilities.extract_value(payload, ["head"])
        self.assignee_emails = okta_tools.get_okta_usernames(self.org, self.team_slug, self.okta_token, self.okta_url, payload)
        self.pr_mentions = self.get_slack_users(client)
        self.merge_commit_sha = utilities.extract_value(payload, ["merge_commit_sha"])

    def get_slack_users(self, client):
        mention_string = ""
        email_list = self.assignee_emails.strip("[]'")
        emails = email_list.split(", ")

        for email in emails:
            try:
                response = client.users_lookupByEmail(email=email)
                user_id = response["user"]["id"]
                mention_string += f" <@{user_id}>"
            except SlackApiError as e:
                print(f"Error tagging user with email {email}: {e.response['error']}")

        return mention_string

# load up class config
def get_variables(payload, repo, org):
    """Get confuration from environment variables."""
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    return vars(client, payload, org, repo)