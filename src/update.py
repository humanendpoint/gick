import os
import re
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta, timezone
import utilities, build, review_handling, github_tools


def handle_modal_submit(payload):
    try:
        pr_number = payload["view"]["blocks"][0]["element"]["action_id"]
        commenter = payload["user"]["username"]
        submission = utilities.extract_value(
            payload, ["view", "state", "values", "comment_made", f"{pr_number}", "value"]
        )
        org = os.environ.get("ORG")
        repo = os.environ.get("REPO")
        domain = os.environ.get("DOMAIN")
        submission_with_commenter = f"{submission}<br><br><br><sub>Comment added by {commenter}@{domain}</sub>"
        github_token = github_tools.get_github_token()
        github_comment_url = (
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/reviews"
        )
        headers = {
            "Authorization": f"Bearer {github_token}", 
            "Accept": "application/vnd.github+json", 
            "X-GitHub-Api-Version": "2022-11-28"
        }
        data = {"body": submission_with_commenter, "event": "COMMENT"}
        response = requests.post(github_comment_url, headers=headers, json=data)
        print(f"GitHub response: {response}")
        return "", 200
    except Exception as e:
        return f"{e}"



def handle_button_click(payload):
    try:
        action_id = payload["actions"][0]["action_id"]
        if action_id.endswith("-com"):
            handle_comment_button_click(payload, action_id)
        elif action_id.endswith("-app") or action_id.endswith("-den"):
            button_click(payload)

    except SlackApiError as e:
        f"{e}", 500
    except Exception as e:
        f"{e}", 500


def button_click(payload):
    actions = utilities.extract_value(payload, ["actions"])
    timestamp = utilities.extract_value(payload, ["message", "ts"])
    pr_title, pr_number, user = utilities.extract_chars(payload)
    decision, decision_message = review_handling.decision_handling(actions, user)
    if "Merge" in decision or "APPROVE" in decision:
        color = "#0B6623"  # green
    elif "Squash" in decision or "REQUEST_CHANGES" in decision:
        color = "#ffd500"  # yellow
    find_and_update_slack_message(decision_message, pr_number, timestamp, color)
    # Ensure that the function returns a response
    return "", 200

def update_slack_message(conf, status, color, timestamp):
    client = WebClient(token=conf.slack_token)
    pr_title = conf.pr_title
    if not update_slack_message_helper(
        client, timestamp, status, pr_title, color
    ):
        print("Message not found or does not match the criteria.")
        return "", 403
    else:
        return "", 200


def find_and_update_slack_message(
    decision, pr_number, timestamp, color
):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    if not find_and_update_slack_message_helper(
        client, decision, pr_number, timestamp, color,
    ):
        print("Message not found or does not match the criteria.")
        return "", 403
    else:
        return "", 200


def send_slack_message(payload):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    try:
        response = client.chat_postMessage(**payload)
        return response
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")
        return None


def handle_comment_button_click(payload, action_id):
    try:
        print(f"comment button payload: {payload}")
        client = WebClient(token=os.environ.get("SLACK_TOKEN"))
        trigger_id = payload["trigger_id"]
        pr_id = action_id.split("-")[0]
        response = client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "PR Comment Entry"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "comment_made",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": pr_id,
                            "multiline": True,
                			"placeholder": {
					            "type": "plain_text",
					            "text": "This will post as the registered GitHub App for PR output."
				            }
                        },
                        "label": {"type": "plain_text", "text": "Enter your comment to add to the PR:"},
                    }
                ],
            },
        )
        print(f"Response from views_open: {response}")
        # Check if the views_open request was successful
        if response["ok"]:
            return "", 200
        else:
            return response["error"]
    except Exception as e:
        return f"{e}"

def update_assignees(pr_title, assignees):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    current_datetime_utc = datetime.now(timezone.utc)
    forty_eight_hours_ago_utc = current_datetime_utc - timedelta(hours=48)
    # Fetch conversation history from the channel within the specified time range
    response = client.conversations_history(
        channel=os.environ.get("CHANNEL_ID"),
        oldest=forty_eight_hours_ago_utc.timestamp(),
        latest=current_datetime_utc.timestamp(),
    )
    messages = response.get("messages", [])
    for message in messages:
        attachments = message.get("attachments", [])
        for attachment in attachments:
            blocks = attachment.get("blocks", [])
            for block in blocks:
                # Check if the block is of type "section" and contains the PR title
                if block.get("type") == "section" and pr_title in block.get("text", {}).get("text", ""):
                    # Update the reviewers' section
                    block_text = block["text"]["text"]
                    reviewers_match = re.search(r'<@(.*?)>', block_text, re.DOTALL)
                    new_block_text = block_text.replace(reviewers_match, assignees)
                    block["text"]["text"] = new_block_text

                    # Send the modified message back to Slack
                    client.chat_update(
                        channel=os.environ.get("CHANNEL_ID"),
                        ts=message["ts"],
                        text=message.get("text", ""),
                        attachments=attachments
                    )


def update_slack_message_helper(client, timestamp, status, pr_title, color):
    response = client.conversations_history(
        channel=os.environ.get("CHANNEL_ID"), latest=timestamp, limit=1, inclusive=True
    )
    messages = response.get("messages", [])
    for message in messages:
        attachments = message.get("attachments", [])
        for attachment in attachments:
            blocks = attachment.get("blocks", [])
            for block in blocks:
                # Check if the block is of type "section" and contains the PR title
                if block.get("type") == "section" and pr_title in block.get("text", {}).get("text", ""):
                    # Iterate through the blocks within this attachment
                    for inner_block in blocks:
                        # Check if the inner block is of type "context" (which contains the "*Checks*: :processing:" text)
                        if inner_block.get("type") == "context":
                            elements = inner_block.get("elements", [])
                            for element in elements:
                                # Check if the element is of type "mrkdwn" and contains "*Checks*: :processing:"
                                if element.get("type") == "mrkdwn" and "*Checks*: :processing:" in element.get("text", ""):
                                    # Update the text with the new status
                                    element["text"] = f"*Checks*: {status}"
                                    # Update the attachment color
                                    attachment["color"] = color
                                    # Prepare the updated message payload
                                    updated_message = {
                                        "channel": os.environ.get("CHANNEL_ID"),
                                        "ts": message["ts"],
                                        "attachments": attachments,
                                    }
                                    # Send the updated message
                                    client.chat_update(**updated_message)
                                    return True
    return False


def find_and_update_slack_message_helper(
    client, decision, pr_number, timestamp, color
):
    response = client.conversations_history(
        channel=os.environ.get("CHANNEL_ID"), oldest=timestamp, limit=1, inclusive=True
    )
    messages = response.get("messages", [])
    for message in messages:
        attachments = message.get("attachments", [])
        for attachment in attachments:
            blocks = attachment.get("blocks", [])
            if blocks:
                # Update only if there are blocks in the attachment
                last_block_index = len(blocks) - 1
                last_block = blocks[last_block_index]
                if last_block.get("type") == "actions":
                    buttons = last_block.get("elements", [])
                    for button in buttons:
                        if button.get("type") == "button":
                            text = button.get("text", {}).get("text", "")
                            if text in ["Merge", "Squash"]:
                                new_block = [
                                    {
                                        "type": "mrkdwn", 
                                        "text": decision
                                    }
                                ]
                                last_block["type"] = "context"
                                last_block["elements"] = new_block
                            elif text == "Approve":
                                pr_creator = button.get("action_id", "").split("-")[1]
                                new_buttons = build.generate_buttons(
                                    pr_number,
                                    pr_creator,
                                    "Merge",
                                    "Request Changes",
                                    "Comment",
                                )
                                last_block["elements"] = new_buttons
                    attachment["blocks"] = blocks
                    attachment["color"] = color

    # Move client.chat_update outside of the loop
    updated_message = {
        "channel": os.environ.get("CHANNEL_ID"),
        "ts": timestamp,
        "as_user": True,
        "attachments": attachments,
    }
    client.chat_update(**updated_message)
    return True if attachments else False
