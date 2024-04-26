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
    if "MERGE" in decision or "APPROVE" in decision:
        color = "#0B6623"  # green
    elif "Squash" in decision or "REQUEST_CHANGES" in decision:
        color = "#ffd500"  # yellow
    assignee_clicked = payload["user"]["id"]
    assignees = re.findall(r"<@(.*?)>", payload["message"]["text"])
    if assignee_clicked in assignees:
        direct_msg_channel = payload["channel"]["id"]
        find_and_update_slack_message(decision_message, pr_number, timestamp, color, direct_msg_channel)
        if "MERGE" in decision:
            pr_channel = os.environ.get("CHANNEL_ID")
            update_chan_on_merge(decision_message, timestamp, pr_channel)
    else:
        if "APPROVE" in decision:
            for assignee in assignees:
                if assignee != assignee_clicked:
                    find_and_remove_slack_message(timestamp, assignee)


def update_slack_message(conf, status, color, timestamp):
    client = WebClient(token=conf.slack_token)
    pr_title = conf.pr_title
    try:
        update_slack_message_helper(
            client, timestamp, status, pr_title, color
        )
    except Exception as e:
        print(f"Error updating Slack message: {e}")


def find_and_update_slack_message(
    decision, pr_number, timestamp, color, channel
):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    try:
        find_and_update_slack_message_helper(
            client, decision, pr_number, timestamp, color, channel
        )

    except Exception as e:
        print(f"Error updating Slack message: {e}")


def send_slack_message(payload, channel=None):
    channel_id = payload.get("channel")
    if not channel_id:
        if channel:
            payload["channel"] = channel
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
					            "text": "This will comment as your registered GitHub App for PR output."
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
            return ""
        else:
            return response["error"]
    except Exception as e:
        return f"{e}"


def update_on_closed(pr_title, decision_message):
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
                    # Update only if there are blocks in the attachment
                    last_block_index = len(blocks) - 1
                    last_block = blocks[last_block_index]
                    if last_block.get("type") == "actions":
                        buttons = last_block.get("elements", [])
                        for button in buttons:
                            if button.get("type") == "button":
                                text = button.get("text", {}).get("text", "")
                                if text in ["Merge", "Approve"]:
                                    new_block = [
                                        {
                                            "type": "mrkdwn", 
                                            "text": decision_message
                                        }
                                    ]
                                    last_block["type"] = "context"
                                    last_block["elements"] = new_block
                        attachment["blocks"] = blocks

                        updated_message = {
                            "channel": os.environ.get("CHANNEL_ID"),
                            "ts": message["ts"],
                            "as_user": True,
                            "attachments": attachments,
                        }
                        # Send the modified message back to Slack
                        client.chat_update(**updated_message)
                    else:
                        print("No need to update message, already merged.")


def find_and_remove_slack_message(timestamp, user_id):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    try:
        response = client.conversations_history(
            channel=user_id,
            latest=timestamp,
            limit=1,
            inclusive=True
        )
        messages = response.get("messages", [])
        for message in messages:
            # Delete the message
            client.chat_delete(channel=user_id, ts=message["ts"])
    except Exception as e:
        print(f"Error removing Slack message for user {user_id}: {e}")


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


def update_chan_on_merge(
    decision, timestamp, channel
):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    response = client.conversations_history(
        channel=channel, oldest=timestamp, limit=1, inclusive=True
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
                            if text == "Comment":
                                new_block = [
                                    {
                                        "type": "mrkdwn", 
                                        "text": decision
                                    }
                                ]
                                last_block.pop("elements", None)
                                last_block["type"] = "context"
                                last_block["elements"] = new_block
                                attachment.pop("color", None)
                                attachment.pop("fallback", None)
                    attachment["blocks"] = blocks

    updated_message = {
        "channel": channel,
        "ts": timestamp,
        "as_user": True,
        "attachments": attachments,
    }
    client.chat_update(**updated_message)


def find_and_update_slack_message_helper(
    client, decision, pr_number, timestamp, color, channel
):
    response = client.conversations_history(
        channel=channel, oldest=timestamp, limit=1, inclusive=True
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
                            if text == "Merge":
                                new_block = [
                                    {
                                        "type": "mrkdwn", 
                                        "text": decision
                                    }
                                ]
                                last_block.pop("elements", None)
                                last_block["type"] = "context"
                                last_block["elements"] = new_block
                                attachment.pop("color", None)
                                attachment.pop("fallback", None)
                            elif text == "Approve":
                                pr_creator = button.get("action_id", "").split("-")[1]
                                new_buttons = build.generate_private_buttons(
                                    pr_number,
                                    pr_creator,
                                    button_approved="Merge",
                                    button_denied="Squash",
                                )
                                last_block["elements"] = new_buttons
                    attachment["blocks"] = blocks
                    attachment["color"] = color

    # Move client.chat_update outside of the loop
    updated_message = {
        "channel": channel,
        "ts": timestamp,
        "as_user": True,
        "attachments": attachments,
    }
    client.chat_update(**updated_message)
