import os
import json
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import jsonify
import utilities, build, review_handling


def handle_modal_submit(request):
    payload = json.loads(request.form["payload"])
    submission = utilities.extract_value(
        payload, ["view", "state", "values", "block_id", "comment_made", "value"]
    )
    org = os.environ.get("ORG")
    repo = os.environ.get("REPO")
    pr_number = submission.split("-")[0]
    github_comment_url = (
        f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/reviews"
    )
    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}
    data = {"body": submission, "event": "COMMENT"}
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
    timestamp = utilities.extract_value(payload, ["message", "ts"])
    decision, decision_message = review_handling.decision_handling(actions, user)
    pr_title, pr_number, user = utilities.extract_chars(payload)
    if "Merge" or "APPROVE" in decision:
        color = "#0B6623"  # green
    elif "Squash" or "REQUEST_CHANGES" in decision:
        color = "#ffd500"  # yellow
    find_and_update_slack_message(
        decision_message, pr_title, pr_number, timestamp, color
    )


def update_slack_message(conf, status, color, timestamp):
    client = WebClient(token=conf.slack_token)
    pr_title = conf.pr_title
    if not update_slack_message_helper(
        client, conf, status, color, timestamp, pr_title
    ):
        print("Message not found or does not match the criteria.")


def find_and_update_slack_message(
    decision, compare_pr_title, pr_number, color, timestamp
):
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    if not find_and_update_slack_message_helper(
        client, decision, compare_pr_title, pr_number, color, timestamp
    ):
        print("Message not found or does not match the criteria.")


def send_slack_message(payload, client):
    try:
        response = client.chat_postMessage(**payload)
        return response
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")
        return None


def handle_comment_button_click(payload_dict):
    # Handle opening comment modal (already implemented)
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    trigger_id = payload_dict["trigger_id"]
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Text Entry"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "comment_made",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "comment_made",
                        "multiline": True,
                    },
                    "label": {"type": "plain_text", "text": "Enter your comment"},
                }
            ],
        },
    )
    return "", 200


def get_message_attachments(client, message):
    bot_id = utilities.get_bot_id(client)
    for attachment in message.get("attachments", []):
        if attachment.get("bot_id") == bot_id:
            return attachment.get("blocks", [])
    return []


def update_slack_message_helper(client, conf, status, color, timestamp, pr_title):
    response = client.conversations_history(
        channel=conf.channel_id, oldest=timestamp, limit=1, inclusive=True
    )
    messages = response.get("messages", [])
    for message in messages:
        attachments = get_message_attachments(client, message)
        for attachment in attachments:
            for block in attachment.get("blocks", []):
                if (
                    block.get("type") == "section"
                    and block.get("text", {}).get("text", "") == pr_title
                ):
                    for inner_attachment in reversed(attachments):
                        blocks = inner_attachment.get("blocks", [])
                        context_blocks = [
                            b for b in blocks if b.get("type") == "context"
                        ]
                        if context_blocks:
                            last_context_block = context_blocks[0]
                            text = (
                                last_context_block.get("elements", [])[0]
                                .get("text", "")
                                .strip()
                            )
                            if text == "*Checks*: :processing:":
                                last_context_block["elements"][0][
                                    "text"
                                ] = f"*Checks*: {status}"
                                inner_attachment["color"] = color
                                updated_attachments = [
                                    a if a["id"] == inner_attachment["id"] else a
                                    for a in attachments
                                ]
                                updated_message = {
                                    "channel": conf.channel_id,
                                    "ts": message["ts"],
                                    "asuser": True,
                                    "attachments": updated_attachments,
                                }
                                client.chat_update(**updated_message)
                                return True
    return False


def find_and_update_slack_message_helper(
    client, decision, compare_pr_title, pr_number, timestamp, color
):
    if color is None:
        color = "#0B6623"
    response = client.conversations_history(
        channel=os.environ.get("CHANNEL_ID"), oldest=timestamp, limit=1, inclusive=True
    )
    messages = response.get("messages", [])
    for message in messages:
        attachments = get_message_attachments(client, message)
        for attachment in attachments:
            for block in attachment.get("blocks", []):
                if block.get("type") == "section" and compare_pr_title in block.get(
                    "text", {}
                ).get("text", ""):
                    for inner_attachment in reversed(attachments):
                        blocks = inner_attachment.get("blocks", [])
                        for block in blocks:
                            if block.get("type") == "actions":
                                last_action_element = block.get("elements", [])[0]
                                if last_action_element.get("type") == "button":
                                    text = last_action_element.get("text", {}).get(
                                        "text", ""
                                    )
                                    if text in ["Merge", "Squash"]:
                                        inner_attachment["blocks"][
                                            blocks.index(block)
                                        ] = {
                                            "type": "context",
                                            "elements": [
                                                {"type": "mrkdwn", "text": decision}
                                            ],
                                        }
                                    elif text == "Approve":
                                        pr_creator = last_action_element.get(
                                            "action_id", ""
                                        )
                                        pr_creator = pr_creator.split("-")[-1]
                                        inner_attachment["blocks"][
                                            blocks.index(block)
                                        ] = {
                                            "type": "actions",
                                            "elements": build.generate_buttons(
                                                pr_number,
                                                pr_creator,
                                                button_merge="Merge",
                                                button_denied="Squash",
                                                button_comment="Comment",
                                            ),
                                        }
                                    inner_attachment["color"] = color
                                    updated_message = {
                                        "channel": os.environ.get("CHANNEL_ID"),
                                        "ts": message["ts"],
                                        "asuser": True,
                                        "attachments": attachments,
                                    }
                                    client.chat_update(**updated_message)
                                    return True
    return False
