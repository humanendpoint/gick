import re
import os
import github_tools


def build_slack_message(conf, repo, pr_number, pr_user_login, channel_id, github_token):
    commit_messages = github_tools.get_commit_messages(conf.org, repo, pr_number, github_token)
    if commit_messages:
        commit_messages_str = ' '.join(commit_messages)  # Join commit messages into a single string
        jira_ticket_ids = re.findall(r"\b[A-Z]+-\d+\b", commit_messages_str)
    else:
        jira_ticket_ids = []
    # hex color values
    red_color = "#ff0000"
    purple_color = "#8A2BE2"
    green_color = "#0B6623"
    yellow_color = "#ffd500"
    # define text
    if "github-actions[bot]" in pr_user_login:
        pretext = f"Pull request opened by <https://github.com/features/actions|{conf.pr_user_login}>"
    else:
        pretext = f"Pull request opened by <https://github.com/{conf.pr_user_login}|{conf.pr_user_login}>"
    jira_text = f"*JIRA*: {jira_ticket_ids}"
    pending_text = "*Checks*: :processing:"
    # gather up the pr info
    pr_info_text = message_building(conf, github_token)
    # build the slack message
    built_message = slack_message_data(
        channel_id,
        pretext,
        pr_info_text,
        jira_text,
        pending_text,
        purple_color,
        red_color,
        pr_user_login,
        pr_number,
        jira_ticket_ids
    )

    return built_message, green_color, yellow_color


def message_building(conf, github_token):
    pr_info_text = ""
    pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    pr_info_text += f"*Reviewers*:\n{conf.pr_mentions}\n\n"
    pr_info_text += "*Files:*\n"
    pr_files = github_tools.get_pr_files(conf, github_token)

    # Construct clickable links for each file
    for file_path in pr_files:
        file_content_url = github_tools.get_file_content_url(conf, file_path, github_token)
        if file_content_url:
            filename = os.path.basename(file_path)
            pr_info_text += f"<{file_content_url}|{filename}>\n"

    return pr_info_text

def create_attachment_block(text):
    attachment = {"pretext": text}

    return attachment


def add_attachment_block(text, color=None):
    attachment = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                },
            }
        ]
    }
    if color is not None:
        attachment["color"] = color
    return attachment


def add_blocks(text=None, color=None, buttons=None):
    attachment = {"blocks": []}
    if text:
        attachment["blocks"].append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
        )
    if buttons:
        attachment["blocks"].append({"type": "actions", "elements": buttons})
    if color:
        attachment["color"] = color

    return attachment


def generate_buttons(
    pr_number, pr_creator, button_approved, button_denied, button_comment
):
    # Define button
    buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": button_approved, "emoji": True},
            "value": button_approved.upper(),
            "action_id": f"{pr_number}-{pr_creator}-app",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": button_denied, "emoji": True},
            "value": button_denied.upper().replace(" ", "_"),
            "action_id": f"{pr_number}-{pr_creator}-den",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": button_comment, "emoji": True},
            "value": button_comment.upper(),
            "action_id": f"{pr_number}-{pr_creator}-com",
        },
    ]

    return buttons


def slack_message_data(
    channel_id,
    pretext,
    pr_info_text,
    jira_text,
    checking_text,
    purple_color,
    red_color,
    pr_creator,
    pr_number,
    jira_ticket_id,
):
    # build attachment blocks
    slack_title = create_attachment_block(pretext)
    slack_pr_info = add_attachment_block(pr_info_text, purple_color)
    # Construct the approval button
    approval_btn = generate_buttons(
        pr_number,
        pr_creator,
        button_approved="Approve",
        button_denied="Request Changes",
        button_comment="Comment",
    )
    slack_pr_status = add_blocks("", red_color, approval_btn)

    if checking_text:
        slack_updated_status = add_blocks(checking_text, purple_color)
        slack_pr_info["blocks"].extend(slack_updated_status["blocks"])

    # If there's a JIRA ticket, add JIRA section
    if jira_ticket_id:
        slack_jira_link = add_blocks(jira_text, purple_color)
        slack_pr_info["blocks"].extend(slack_jira_link["blocks"])

    # concatenate all the blocks
    built_slack_message = {
        "channel": channel_id,
        "attachments": [slack_title, slack_pr_info, slack_pr_status],
    }

    return built_slack_message
