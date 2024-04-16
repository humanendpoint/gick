from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from google.cloud import iam_v1
import time
import os
import github_tools

class slackbot:
    def __init__(self, slack_token, project_id):
        self.slack_client = WebClient(token=slack_token)
        self.iam_client = iam_v1.IAMClient()
        self.project_id = project_id


    def add_user_to_project(self, user_id, role):
        try:
            user_info = self.slack_client.users_info(user=user_id)
            if user_info['ok']:
                email = user_info['user']['profile']['email']
                policy = self.iam_client.get_policy(request={"resource": f"projects/{self.project_id}"})
                binding = next((b for b in policy.bindings if b.role == role), None)
                if binding:
                    binding.members.append(f"user:{email}")
                else:
                    binding = {"role": role, "members": [f"user:{email}"]}
                    policy.bindings.append(binding)
                self.iam_client.set_iam_policy(request={"resource": f"projects/{self.project_id}", "policy": policy})
                return True, f"User {email} added to project {self.project_id} with role {role}"
            else:
                return False, "Failed to fetch user info from Slack"
        except SlackApiError as e:
            error_message = f"Slack API error: {e.response['error']}"
            print(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return False, error_message


    def rate_limit(self, func):
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if 'last_call_time' not in wrapper.__dict__ or current_time - wrapper.__dict__['last_call_time'] > 1:
                wrapper.__dict__['last_call_time'] = current_time
                return func(*args, **kwargs)
            else:
                error_message = "Rate limit exceeded. Please wait before making another call."
                print(error_message)
                return False, error_message
        return wrapper


    @rate_limit
    def add_user_safely(self, user_id, role):
        success, message = self.add_user_to_project(user_id, role)
        if success:
            self.log_info(message)
        else:
            print(message)
        return success, message


    def handle_slack_command(self, command, text, user_id):
        if command == "/gcp-add":
            return self.add_user_to_project_command(text, user_id)
        elif command == "/gh":  # Add this block for /gh command
            return self.handle_gh_command(text, user_id)
        elif command == "/trigger-workflow":  # New command for triggering GitHub workflow
            return self.handle_trigger_workflow_command(text)
        else:
            return False, "Unknown command"


    def add_user_to_project_command(self, text, user_id):
        command_parts = text.split()
        if len(command_parts) == 2:
            project_id = command_parts[0]
            role = command_parts[1]

            success, message = self.add_user_safely(user_id, role)
            if success:
                return True, {"message": message}
            else:
                return False, {"error": message}
        else:
            return False, {"error": "Invalid command format. Please use: /add-user-to-project PROJECT_ID ROLE"}


    def handle_gh_workflow_command(self, text):
        try:
            # Extract required parameters from the command text
            params = text.split('"')
            if len(params) < 3:
                return False, "Invalid command format. Please provide the reference branch, workflow name, and inputs (if required)."
            reference_branch = params[1].strip()
            workflow_name = params[3].strip()
            inputs = params[5].strip() if len(params) > 5 else None
            
            # Trigger GitHub workflow dispatch event
            github_tools.trigger_workflow_dispatch(reference_branch, workflow_name, inputs)
            
            return True, f"GitHub workflow '{workflow_name}' dispatched successfully."
        except Exception as e:
            return False, f"Failed to trigger GitHub workflow: {str(e)}"

    def handle_gh_command(body, client, command):
        user_id = body["user_id"]
        # Extract title, description, and target branch from the command
        text = command["text"]
        params = text.split('"')
        
        if len(params) < 4:  # Check if all required parameters are provided
            # If any required parameter is missing, send usage instructions
            client.chat_postEphemeral(
                user=user_id,
                text="To create a pull request, use `/gh create \"repo\" \"title\" \"description\" \"head branch\"`"
            )
            return

        org = os.environ.get("GITHUB_ORG")
        if not org:
            client.chat_postEphemeral(
                user=user_id,
                text="GitHub organization is not configured."
            )
            return

        repo = params[1]
        title = params[2]
        description = params[3] if len(params) >= 4 else ""
        head_branch = params[4] if len(params) >= 5 else "master"
        try:
            response = github_tools.create_pull_request(org, repo, title, description, head_branch)
            client.chat_postMessage(
                channel=os.environ.get("CHANNEL_ID"),
                text=f"Pull request created from /gh cmd: {response['html_url']}"
            )
        except SlackApiError as e:
            client.chat_postEphemeral(
                user=user_id,
                text=f"Failed to create pull request: {str(e)}"
            )
        except Exception as e:
            client.chat_postEphemeral(
                user=user_id,
                text=f"An error occurred: {str(e)}"
            )