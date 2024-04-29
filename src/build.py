import re
import os
import github_tools

MAX_MESSAGE_LENGTH = 4000


def build_slack_message(conf, repo, pr_number, pr_user_login, channel_id, github_token):
    commit_messages = github_tools.get_commit_messages(
        conf.org, repo, pr_number, github_token
    )
    if commit_messages:
        commit_messages_str = " ".join(
            commit_messages
        )  # Join commit messages into a single string
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
    jira_text = f"*JIRA*: {jira_ticket_ids[0]}"
    pending_text = "*Checks*: :processing:"
    org_and_repo = f":github: {conf.org}/{repo}"
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
        jira_ticket_ids,
        org_and_repo,
    )
    dm_pr_info_text = private_message_building(conf, github_token)
    built_dm = generate_priv_message(
        pr_number,
        pr_user_login,
        dm_pr_info_text,
        purple_color,
    )

    return built_dm, built_message, green_color, yellow_color


def private_message_building(conf, github_token):
    diff_url = (
        f"https://api.github.com/repos/{conf.org}/{conf.repo}/pulls/{conf.pr_number}"
    )
    dm_pr_info_text = ""
    dm_pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    dm_pr_info_text += f"*Created by:* {conf.pr_user_login}\n"
    dm_pr_info_text += f"*All assignees:* {conf.pr_mentions}\n\n"
    diff_content = github_tools.get_diff_content(diff_url, github_token)
    if diff_content:
        diff_message = construct_diff_msg(diff_content)
        if len(dm_pr_info_text) + len(diff_message) > MAX_MESSAGE_LENGTH:
            dm_pr_info_text += "*PR Diffs:*\nMessage exceeds character limit. "
            dm_pr_info_text += f"<{conf.pr_url}|Link to PR>"
        else:
            dm_pr_info_text += "*PR Diffs:*\n" + diff_message

    return dm_pr_info_text


def construct_diff_msg(payload):
    lines = payload.split("\n")
    formatted_diff = ""
    current_file = None
    for line in lines:
        if line.startswith("diff --git"):
            if current_file:
                formatted_diff += "```\n"
            filename = line.split(" b/")[-1]
            formatted_diff += f"Diff for file: {filename}\n```\n"
            current_file = filename
            continue
        if current_file:
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            elif (
                line.startswith("index ")
                or line.startswith("new file ")
                or line.startswith("deleted file ")
            ):
                continue
            elif line.startswith(" ") or line.startswith("+") or line.startswith("-"):
                if line.startswith(" "):
                    formatted_diff += f"  {line.strip()}\n"
                elif line.startswith("+"):
                    formatted_diff += f"+ {line.strip()}\n"
                elif line.startswith("-"):
                    formatted_diff += f"- {line.strip()}\n"
    if current_file:
        formatted_diff += "```\n"
    return formatted_diff


def message_building(conf, github_token):
    pr_info_text = ""
    pr_info_text += f"<{conf.pr_url}|#{conf.pr_number} {conf.pr_title}>\n"
    pr_info_text += f"*Reviewers*:\n{conf.pr_mentions}\n\n"
    pr_info_text += "*Files:*\n"
    pr_files = github_tools.get_pr_files(conf, github_token)

    # Construct clickable links for each file
    for file_path in pr_files:
        file_content_url = github_tools.get_file_content_url(
            conf, file_path, github_token
        )
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


def generate_button(pr_number, pr_creator, button_comment):
    # Define button
    button = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": button_comment, "emoji": True},
            "value": button_comment.upper(),
            "action_id": f"{pr_number}-{pr_creator}-com",
        },
    ]

    return button


def generate_private_buttons(pr_number, pr_creator, button_approved, button_denied):
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
    org_and_repo,
):
    # build attachment blocks
    slack_title = create_attachment_block(pretext)
    slack_pr_info = add_attachment_block(pr_info_text, purple_color)
    # Construct the approval button
    comment_btn = generate_button(
        pr_number,
        pr_creator,
        button_comment="Comment",
    )
    slack_pr_status = add_blocks("", red_color, comment_btn)

    if checking_text:
        slack_updated_status = add_blocks(checking_text, purple_color)
        slack_pr_info["blocks"].extend(slack_updated_status["blocks"])

    # If there's a JIRA ticket, add JIRA section
    if jira_ticket_id:
        slack_jira_link = add_blocks(jira_text, purple_color)
        slack_pr_info["blocks"].extend(slack_jira_link["blocks"])

    if org_and_repo:
        org_and_repo = add_blocks(org_and_repo, purple_color)
        slack_pr_info["blocks"].extend(org_and_repo["blocks"])
    # concatenate all the blocks
    built_slack_message = {
        "channel": channel_id,
        "attachments": [slack_title, slack_pr_info, slack_pr_status],
    }

    return built_slack_message


def generate_priv_message(pr_number, pr_creator, pr_info_text, purple_color):
    title_text = create_attachment_block("A new :github: GitHub PR assigned to you:")
    pr_info = add_attachment_block(pr_info_text, purple_color)
    approval_btns = generate_private_buttons(
        pr_number,
        pr_creator,
        button_approved="Approve",
        button_denied="Request Changes",
    )
    created_buttons = add_blocks("", purple_color, approval_btns)
    pr_info["blocks"].extend(created_buttons["blocks"])
    built_dm_message = {
        "attachments": [title_text, pr_info],
    }

    return built_dm_message
