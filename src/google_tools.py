import os
import interactive

bot = interactive.slackbot(os.environ.get("SLACK_TOKEN"), os.environ.get("PROJECT_ID"))

def add_user_to_project_command(text, user_id, bot):
    # Extract project ID and role from the command
    # the command format is '/add-user-to-project PROJECT_ID ROLE'
    command_parts = text.split()
    if len(command_parts) == 2:
        project_id = command_parts[0]
        role = command_parts[1]
        
        # Add user to project using SlackBot instance
        success, message = bot.add_user_safely(user_id, role)
        if success:
            return {"message": message}, 200
        else:
            return {"error": message}, 500
    else:
        return {"error": "Invalid command format. Please use: /add-user-to-project PROJECT_ID ROLE"}, 400