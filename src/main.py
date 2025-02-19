import json
import os
from flask import Response
import utilities, update, build, variables, github_tools, skiplist, approvedlist

def main(request):
    """Handling incoming request"""
    try:
        if request.content_type == "application/x-www-form-urlencoded":
            raw_payload = request.form.get("payload")
            payload_body = json.loads(raw_payload)
            event_type = payload_body.get("type")
            if event_type == "interactive_message":
                update.handle_button_click(payload_body)
            elif event_type == "block_actions":
                update.handle_button_click(payload_body)
            elif event_type == "view_submission":
                update.handle_modal_submit(payload_body)
        if request.content_type == "application/json":
            payload_body = request.get_json()
            event_type = payload_body.get("type")
            if event_type == "url_verification":
                challenge = utilities.extract_value(payload_body, ["challenge"])
                response_content = json.dumps({"challenge": challenge})
                response = Response(
                    response_content, status=200, content_type="application/json"
                )
                response.headers.add("HTTP", "200 OK")
                return response
            else:
                action = utilities.extract_value(payload_body, ["action"])
                if action in skiplist.SKIPPED_ACTIONS:
                    return "Skipping", 200
                elif action in approvedlist.APPROVED_ACTIONS:
                    payload = utilities.extract_value(payload_body, ["pull_request"])
                    org = utilities.extract_value(payload_body, ["organization", "login"])
                    repo = utilities.extract_value(payload_body, ["repository", "name"])
                    github_token = github_tools.get_github_token() 
                    conf = variables.get_variables(payload, repo, org, github_token)
                    signature_header = request.headers.get("X-Hub-Signature-256")
                    payload_validation = json.dumps(request.get_json())
                    utilities.verify_signature(
                        payload_validation, conf.webhook_secret_token, signature_header
                    )
                    print("Verified the signature.")
                    if any(title in payload_body.get("pull_request", {}).get("title", "") for title in skiplist.SKIPPED_TITLES):
                        return "Skipping", 200
                    if action == "opened":
                        try:
                            built_dm, built_message, green_color, yellow_color = build.build_slack_message(
                                conf, conf.repo, conf.pr_number, conf.pr_user_login, conf.channel_id, github_token
                            )
                            response = update.send_slack_message(built_message)
                            timestamp = utilities.extract_value(response, ["message", "ts"])
                            status = utilities.wait_for_checks(conf.org, conf.repo, github_token, conf.merge_commit_sha)
                            if "Passing" in status:
                                color = green_color
                            else:
                                color = yellow_color
                            update.update_slack_message(conf, status, color, timestamp)
                            dm_assignee = conf.pr_mentions.replace("<@", "").replace(">", "").split()
                            for assignee in dm_assignee:
                                print(f"Sending private message to {assignee}")
                                update.send_slack_message(built_dm, assignee)
                        except Exception as e:
                            print(f"We have an error: {e}")
                    elif action == "closed":
                        #decision_message = ":tada: Merged! (via web)"
                        #update.update_on_closed(
                        #    conf.pr_title,
                        #    decision_message
                        #)
                        print("Not doing this yet.")
                    elif action == "reopened":
                        #built_message, green_color, yellow_color = build.build_slack_message(
                        #    conf, conf.repo, conf.pr_number, conf.pr_user_login, conf.channel_id, github_token
                        #)
                        #status = utilities.wait_for_checks(conf, github_token)
                        #update.update_slack_message(conf, status, yellow_color)
                        print("Not doing this yet.")
                    return "", 200
                else:
                    print("Did not find an actionable action, skipping.")
                    return "Processed, skipping", 200
    except Exception as e:
        return f"Error processing request: {str(e)}", 500