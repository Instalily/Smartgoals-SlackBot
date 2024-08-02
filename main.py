import os
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import functions_framework
import pytz
from fastapi import FastAPI

app = FastAPI()
load_dotenv()

CHANNEL_ID = os.getenv('SLACK_CHANNEL_ID')
slack_token = os.getenv('SLACK_BOT_TOKEN')
slack_client = WebClient(token=slack_token)

specific_users = [
    "Cristin Connerney", "Logan Ge", "Dhiraj Khanal", "Iris Cheng", "Mateo Godoy", "Hongyi Wu", 
    "Prashanthi Ramachandran", "Morgann Thain", "Joshua Shou", "Geneva", "Sujit Varadhan", 
    "Laryn Qi", "Edward Kim", "Sriyans Rauniyar", "Zubin Chandra", "Doris Huang", "Alex Kim", 
    "Mars Tan", "Aris Zhu", "Brigit Jacob", "Jack Rangaiah", "Roey Abehsera"
] # To make sure it only checks for messages sent by those posting Smartgoals

def get_user_name(user_id):
    try:
        result = slack_client.users_info(user=user_id)
        return result['user']['real_name']
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response['error']}")
        return None

def extract_messages(channel_id):
    try:
        est = pytz.timezone('US/Eastern')
        now = datetime.now(tz=est)
        
        start_time = now - timedelta(days=1)
        end_time = now  

        oldest_time = int(start_time.timestamp())
        latest_time = int(end_time.timestamp())

        result = slack_client.conversations_history(
            channel=channel_id,
            oldest=oldest_time,
            latest=latest_time
        )
        return result['messages']
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
        return []

def process_messages(messages):
    est = pytz.timezone('US/Eastern')
    today_date = datetime.now(tz=est).date()
    global submitted_users, not_submitted_users
    submitted_users = {}
    not_submitted_users = set(specific_users)


    for msg in messages:
        user = msg.get('user')
        if user:
            username = get_user_name(user)
            if username and username in specific_users:
                timestamp = datetime.fromtimestamp(float(msg['ts']), tz=est)

                
                submitted_users[username] = timestamp
                not_submitted_users.discard(username)
    
    return

def send_slack_message():
    try:
        est = pytz.timezone('US/Eastern')
        today_date = datetime.now(tz=est).strftime('%Y-%m-%d')
        header_message = f"*Daily Update - {today_date}*\n"
        
        # Format Submitted Users
        submitted_users_message = "\n*Submitted Users:*\n"
        sorted_submitted_users = sorted(submitted_users.items(), key=lambda x: x[1])
        submitted_users_message += "```"
        submitted_users_message += "Name           | Timestamp\n"
        submitted_users_message += "---------------|----------------\n"
        for user, timestamp in sorted_submitted_users:
            submitted_users_message += f"{user:<15} | {timestamp.strftime('%I:%M %p')}\n"
        submitted_users_message += "```"

        # Format Not Submitted Users
        not_submitted_users_message = "\n*Not Submitted Users:*\n"
        not_submitted_users_message += "```"
        not_submitted_users_message += "Name\n"
        not_submitted_users_message += "---------------\n"
        for user in not_submitted_users:
            not_submitted_users_message += f"{user}\n"
        not_submitted_users_message += "```"

        
        def split_message(message, max_length=4000):
            return [message[i:i+max_length] for i in range(0, len(message), max_length)]

        # Prepare all chunks for Slack messages
        chunks = split_message(header_message + submitted_users_message + not_submitted_users_message)
        
        # channel_id = "C07CBL4DE30"  # Replace with your destination channel ID, C07CBL4DE30 = Actual Channel, C07DT2TQDDJ = Test Channel
        
        for chunk in chunks:
            response = slack_client.chat_postMessage(channel=CHANNEL_ID, text=chunk)
            if response["ok"]:
                print(f"Data sent to channel {CHANNEL_ID} on Slack.")
            else:
                print(f"Failed to send message to channel {CHANNEL_ID}: {response['error']}")

    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def process_slack_smart_goals():
    channel_id = 'C057AFRT9SN'
    messages = extract_messages(channel_id)
    if messages:
        process_messages(messages)
        send_slack_message()
    else:
        print("No messages fetched from Slack.")

@app.get("/")
async def hello():
    return ("THe app is live and running")

@app.get("/run-slack-smart-goals")
async def run_slack_smart_goals():
    try:
        process_slack_smart_goals()
        return {"status": "success", "message": "Slack Smart Goals were procesed successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}