import os
import json
import requests
import utilities, build, review_handling
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta, timezone
from flask import jsonify

def handle_modal_submit(request):
    payload = json.loads(request.form['payload'])
    submission = utilities.extract_value(payload, ['view', 'state', 'values', 'block_id', 'comment_made', 'value'])
    org = os.environ.get("ORG")
    repo = os.environ.get("REPO")
    pr_number = submission.split('-')[0]
    github_comment_url = f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/reviews"
    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}
    data = {"body": submission, "event":{}}
    response = requests.post(github_comment_url, headers=headers, json=data)

    return response

def handle_button_click(request):
    response = None
    payload = request.form.get("payload")
    payload = json.loads(payload)
    action_id = payload["actions"][0]["action_id"]
    try:
        if action_id.endswith("-com"):
            response = handle_comment_button_click(payload)
        elif action_id.endswith("-app") or action_id.endswith("-den"):
            response = handle_button_click(payload)
    except SlackApiError as e:
        return jsonify({"error": str(e)}), 500

    return response

def handle_button_click(request):
    raw_payload = request.form.get("payload")
    payload = json.loads(raw_payload)
    actions = utilities.extract_value(payload, ["actions"])
    decision, decision_message = review_handling.decision_handling(actions, user)
    pr_title, pr_number, user = utilities.extract_chars(payload)
    if "Merge" or "APPROVE" in decision:
        color = "#0B6623" # green
    elif "Squash" or "REQUEST_CHANGES" in decision:
        color = "#ffd500" # yellow
    find_and_update_slack_message(decision_message, pr_title, pr_number, color)

def handle_comment_button_click(payload_dict):
    # Handle opening comment modal (already implemented)
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    trigger_id = payload_dict["trigger_id"]
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Text Entry"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "comment_made",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "comment_made",
                        "multiline": True,
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Enter your comment"
                    }
                }
            ]
        }
    )
    return '', 200

def find_and_update_slack_message(decision, compare_pr_title, pr_number, color):
    # Initialize the Slack WebClient
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    # Get the current datetime in UTC and three hours ago
    current_datetime_utc = datetime.now(timezone.utc)
    twenty_four_hours_ago_utc = current_datetime_utc - timedelta(hours=24)
    # Fetch conversation history from the channel within the specified time range
    response = client.conversations_history(
        channel=os.environ.get("CHANNEL_ID"),
        oldest=twenty_four_hours_ago_utc.timestamp(),
        latest=current_datetime_utc.timestamp(),
    )
    # Extract messages from the response
    messages = response["messages"]
    # Flag to indicate if the message is found
    message_found = False
    bot_id = utilities.get_bot_id(client)
    # Iterate through the messages
    for message in messages:
        # Check if the message is from the bot and matches the criteria
        if "bot_id" in message and message["bot_id"] == bot_id:
            attachments = message.get("attachments", [])
            pr_title_matched = False
            # Iterate through attachments to find the blocks
            for attachment in attachments:
                blocks = attachment.get("blocks", [])
                # Check if this attachment has a section block with PR title
                for block in blocks:
                    if block.get("type") == "section":
                        pr_title = block.get("text", {}).get("text", "")
                        if compare_pr_title in pr_title:
                            pr_title_matched = True
                            break
                # If PR title matched, update the last context block
                if pr_title_matched:
                    for attachment in reversed(attachments):
                        if "blocks" in attachment:
                            # Find the last actions block and update it
                            for idx, block in enumerate(reversed(attachment["blocks"])):
                                if block.get("type") == "actions":
                                    last_action_block_index = (
                                        len(attachment["blocks"]) - 1 - idx
                                    )
                                    last_action_block = attachment["blocks"][
                                        last_action_block_index
                                    ]
                                    if last_action_block.get("elements"):
                                        last_action_element = last_action_block[
                                            "elements"
                                        ][0]
                                        # Check if last_action_element is a button
                                        if last_action_element.get("type") == "button":
                                            # No need to strip here as it's not text
                                            last_action_element_text = (
                                                last_action_element.get("text", {}).get(
                                                    "text", ""
                                                )
                                            )
                                            if last_action_element_text == "Merge" or last_action_element_text == "Squash":
                                                # Replace the last action block with a context block
                                                attachment["blocks"][
                                                    last_action_block_index
                                                ] = {
                                                    "type": "context",
                                                    "elements": [
                                                        {
                                                            "type": "mrkdwn",
                                                            "text": decision,
                                                        }
                                                    ],
                                                }

                                            if last_action_element_text == "Approve":
                                                # Replace the last action block with a context block
                                                pr_creator = last_action_element.get("action_id", "")
                                                attachment["blocks"][
                                                    last_action_block_index
                                                ] = {
                                                    "type": "actions",
                                                    "elements": build.generate_buttons(
                                                        pr_number, 
                                                        pr_creator, 
                                                        button_merge="Merge", 
                                                        button_denied="Squash", 
                                                        button_comment="Comment"),
                                                }

                                            attachment["color"] = color
                                            updated_message = {
                                                "channel": os.environ.get(
                                                    "CHANNEL_ID"
                                                ),
                                                "ts": message["ts"],
                                                "asuser": True,
                                                "attachments": attachments,
                                            }
                                            client.chat_update(**updated_message)
                                            message_found = True
                                            break
                        if message_found:
                            break
                if message_found:
                    break

    if not message_found:
        print("Message not found or does not match the criteria.")

def update_slack_message(conf, status, color):
    # Initialize the Slack WebClient
    client = WebClient(token=conf.slack_token)
    # Get the current datetime in UTC and three hours ago
    current_datetime_utc = datetime.now(timezone.utc)
    twenty_four_hours_ago_utc = current_datetime_utc - timedelta(days=30)
    # Fetch conversation history from the channel within the specified time range
    response = client.conversations_history(
        channel=conf.channel_id,
        oldest=twenty_four_hours_ago_utc.timestamp(),
        latest=current_datetime_utc.timestamp(),
    )
    # Extract messages from the response
    messages = response["messages"]
    # Flag to indicate if the message is found
    message_found = False
    bot_id = utilities.get_bot_id(client)
    # Iterate through the messages
    for message in messages:
        # Check if the message is from the bot and matches the criteria
        if "bot_id" in message and message["bot_id"] == bot_id:
            attachments = message.get("attachments", [])
            pr_title_matched = False
            # Iterate through attachments to find the blocks
            for attachment in attachments:
                blocks = attachment.get("blocks", [])
                # Check if this attachment has a section block with PR title
                for block in blocks:
                    if block.get("type") == "section":
                        pr_title = block.get("text", {}).get("text", "")
                        # Check if PR title matches the one from environment variable
                        if conf.pr_title in pr_title:
                            pr_title_matched = True
                            break
                # If PR title matched, update the matched context block
                if pr_title_matched:
                    for attachment in reversed(attachments):
                        if "blocks" in attachment:
                            context_blocks = [
                                block
                                for block in attachment["blocks"]
                                if block.get("type") == "context"
                            ]
                            if context_blocks:
                                last_context_block = context_blocks[0]
                                last_context_block_text = (
                                    last_context_block.get("elements", [])[0]
                                    .get("text", "")
                                    .strip()
                                )
                                # Update the context block if it has the desired text
                                if last_context_block_text == "*Checks*: :processing:":
                                    last_context_block["elements"][0][
                                        "text"
                                    ] = f"*Checks*: {status}"
                                    attachment["color"] = color
                                    updated_attachments = [
                                        attachment if a["id"] == attachment["id"] else a
                                        for a in attachments
                                    ]
                                    updated_message = {
                                        "channel": conf.channel_id,
                                        "ts": message["ts"],
                                        "asuser": True,
                                        "attachments": updated_attachments,
                                    }
                                    client.chat_update(**updated_message)
                                    message_found = True
                                    break
                    if message_found:
                        break

    if not message_found:
        print("Message not found or does not match the criteria.")

def send_slack_message(payload, client):
    try:
        response = client.chat_postMessage(**payload)
        return response
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")
        return None