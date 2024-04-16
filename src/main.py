import json
from flask import jsonify, Response
import utilities, update, build, variables, github_tools

def main(request):
    """Handling incoming request"""
    try:
        if request.content_type == "application/x-www-form-urlencoded":
            raw_payload = request.form.get("payload")
            payload_body = json.loads(raw_payload)
            event_type = payload_body.get("type")
            print(f"payload body: {payload_body}")
            if event_type == "interactive_message":
                update.handle_button_click(payload_body)
            elif event_type == "block_actions":
                update.handle_button_click(payload_body)
            elif event_type == "view_submission":
                update.handle_modal_submit(payload_body)
        if request.content_type == "application/json":
            payload_body = request.get_json()
            event_type = payload_body.get("type")
            # Code mainly for handling GitHub webhook payload
            # but first test if this is a Slack url verification request:
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
                if action in [
                    "assigned",
                    "auto_merge_disabled",
                    "auto merge_enabled",
                    "unassigned", 
                    "converted_to_draft", 
                    "milestoned",
                    "demilestoned", 
                    "dequeued", 
                    "edited", 
                    "enqueued", 
                    "labeled", 
                    "locked", 
                    "ready_for_review", 
                    "review_request_removed", 
                    "review_requested",
                    "synchronized", 
                    "unlabeled", 
                    "unlocked"
                ]:
                    return "Skipping", 200
                elif action in ["opened", "closed", "reopened"]:
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
                    if any(title in payload_body.get("pull_request", {}).get("title", "") for title in ["munki apps", "[skip ci] Serial"]):
                        print("Doing nothing, this is a skipped webhook")
                        return "Skipping", 200
                    if action == "opened":
                        print("Building the slack message...")
                        built_message, green_color, yellow_color = build.build_slack_message(
                            conf, conf.repo, conf.pr_number, conf.pr_user_login, conf.channel_id, github_token
                        )
                        response = update.send_slack_message(built_message)
                        timestamp = utilities.extract_value(response, ["message", "ts"])
                        status = utilities.wait_for_checks(conf.org, conf.repo, github_token, conf.merge_commit_sha)
                        update.update_slack_message(conf, status, green_color, timestamp)
                    elif action == "closed":
                        #decision_message = ":tada: Merged! (via web)"
                        #update.find_and_update_slack_message(
                        #    decision_message,
                        #    conf.pr_title,
                        #    conf.pr_number,
                        #    timestamp,
                        #    color=None,
                        #)
                        print("Not doing this yet")
                    elif action == "reopened":
                        built_message, green_color, yellow_color = build.build_slack_message(
                            conf, conf.repo, conf.pr_number, conf.pr_user_login, conf.channel_id, github_token
                        )
                        status = utilities.wait_for_checks(conf, github_token)
                        update.update_slack_message(conf, status, yellow_color)
                    return "Processed", 200
                else:
                    print("Did not find an actionable action, skipping.")
                    return "Processed, skipping", 200
    except Exception as e:
        return f"Error processing request: {str(e)}", 500