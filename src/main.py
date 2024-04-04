import json
from flask import Flask, request, jsonify, Response
import utilities, update, build, variables

app = Flask(__name__)

@app.route('/slack/modal-submit', methods=['POST'])
def handle_modal_submit():
    response = update.handle_modal_submit(request)
    if response.status_code == 201:
        return jsonify({"message": "Comment added successfully"}), 200
    else:
        return jsonify({"error": "Failed to add comment"}), 500

@app.route('/slack/button-click', methods=['POST'])
def handle_button_click():
    response = update.handle_button_click(request)
    return response

def main(request):
    """Handling incoming request"""
    try:
        if request.content_type == "application/json":
            payload_body = request.get_json()
            # Code mainly for handling GitHub webhook payload
            # but first test if this is a Slack url verification request:
            if "type" in payload_body and payload_body["type"] == "url_verification":
                challenge = payload_body["challenge"]
                response_content = json.dumps({"challenge":challenge})
                response = Response(response_content, status=200, content_type="application/json")
                response.headers.add("HTTP", "200 OK")
                return response
            org = utilities.extract_value(payload_body, ["organization"])
            repo = utilities.extract_value(payload_body, ["repository"])
            payload = utilities.extract_value(payload_body, ["pull_request"])
            conf = variables.get_variables(payload, repo, org)
            signature_header = request.headers.get("X-Hub-Signature-256")
            utilities.verify_signature(payload_body, conf.webhook_secret_token, signature_header)
            if utilities.extract_value(payload_body, ["action"]) == "opened":
                built_message, green_color, yellow_color = build.build_slack_message(conf)
                response = update.send_slack_message(built_message)
                timestamp = utilities.extract_value(response, ["message", "ts"])
                status = utilities.wait_for_checks(conf)
                update.update_slack_message(conf, status, green_color, timestamp)
            elif utilities.extract_value(payload_body, ["action"]) == "closed":
                decision_message = ":tada: Merged! (via web)"
                update.find_and_update_slack_message(decision_message, conf.pr_title, conf.pr_number, timestamp, color=None)
            elif utilities.extract_value(payload_body, ["action"]) == "reopened":
                built_message, green_color, yellow_color = build.build_slack_message(conf)
                status = utilities.wait_for_checks(conf)
                update.update_slack_message(conf, status, yellow_color)
    except Exception as e:
        return f"Error processing request: {str(e)}", 500
