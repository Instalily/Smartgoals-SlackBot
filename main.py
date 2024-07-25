import os
from datetime import datetime, timedelta
import csv
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI
from dotenv import load_dotenv
import functions_framework

load_dotenv()

slack_token = os.getenv('SLACK_BOT_TOKEN')
openai_api_key = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=openai_api_key)
slack_client = WebClient(token=slack_token)

specific_users = [
    "Cristin Connerney", "Logan Ge", "Dhiraj Khanal", "Iris Cheng", "Mateo Godoy", "Hongyi Wu", 
    "Prashanthi Ramachandran", "Morgann Thain", "Joshua Shou", "Geneva", "Sujit Varadhan", 
    "Laryn Qi", "Edward Kim", "Sriyans Rauniyar", "Zubin Chandra", "Doris Huang", "Alex Kim", 
    "Mars Tan", "Aris Zhu", "Brigit Jacob", "Jack Rangaiah", "Roey Abehsera"
] # To make sure it only checkes for messages sent by those posting Smartgoals

def get_user_name(user_id):
    try:
        result = slack_client.users_info(user=user_id)
        return result['user']['real_name']
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response['error']}")
        return None

def extract_messages(channel_id):
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
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

def extract_date_from_text(text):
    # Define date patterns for various formats
    date_patterns = [
        r'\b(\d{4}-\d{2}-\d{2})\b',       # YYYY-MM-DD
        r'\b(\d{2}/\d{2}/\d{4})\b',       # MM/DD/YYYY
        r'\b(\d{2}-\d{2}-\d{4})\b'        # DD-MM-YYYY
    ]
    
    # Extract date from the beginning of the text
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(match.group(1), '%m/%d/%Y').date()
                except ValueError:
                    return datetime.strptime(match.group(1), '%d-%m-%Y').date()
    return None

def process_messages(messages):
    today_date = datetime.now().date()
    processed_data = []
    global submitted_users, not_submitted_users
    submitted_users = {}
    not_submitted_users = set(specific_users)
    
    categorized_messages = {}

    for msg in messages:
        user = msg.get('user')
        if user:
            username = get_user_name(user)
            if username and username in specific_users:
                timestamp = datetime.fromtimestamp(float(msg['ts']))
                text = msg['text']
                date_mentioned = extract_date_from_text(text) or today_date
                
                # Categorize messages by the mentioned date
                if date_mentioned not in categorized_messages:
                    categorized_messages[date_mentioned] = []
                
                categorized_messages[date_mentioned].append({
                    'user': username,
                    'timestamp': timestamp,
                    'text': text,
                    'summary': generate_summary(text)
                })
                
                if date_mentioned == today_date:
                    submitted_users[username] = timestamp
                    not_submitted_users.discard(username)
    
    return categorized_messages

def generate_summary(text):
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant, summarizing today's work completed by each person for their boss in a very short and concise way."},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary."

def save_to_csv(categorized_data):
    csv_filename = '/tmp/slack_smart_goals.csv'
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'date', 'summary']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            csvfile.write("Submitted Users:\n")
            for user, timestamp in submitted_users.items():
                csvfile.write(f"{user} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            csvfile.write("\n")

            csvfile.write("Not Submitted Users:\n")
            for user in not_submitted_users:
                csvfile.write(f"{user}\n")
            csvfile.write("\n")

            writer.writeheader()
            for date, messages in categorized_data.items():
                for item in messages:
                    writer.writerow({
                        'name': item['user'],
                        'date': item['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        'summary': item['summary']
                    })
        print(f"Data saved to {csv_filename}")
    except IOError as e:
        print(f"Error saving to CSV: {e}")

def send_slack_message(categorized_data):
    try:
        today_date = datetime.now().strftime('%Y-%m-%d')
        header_message = f"*Daily Update - {today_date}*\n"
        
        submitted_users_message = "\n*Submitted Users:*\n"
        not_submitted_users_message = "\n\n*Not Submitted Users:*\n"

        sorted_submitted_users = sorted(submitted_users.items(), key=lambda x: x[1])

        submitted_users_message += "```"
        submitted_users_message += "Name           | Timestamp\n"
        submitted_users_message += "---------------|----------------\n"
        for user, timestamp in sorted_submitted_users:
            submitted_users_message += f"{user:<15} | {timestamp.strftime('%I:%M %p')}\n"
        submitted_users_message += "```"

        not_submitted_users_message += "```"
        not_submitted_users_message += "Name\n"
        not_submitted_users_message += "---------------\n"
        for user in not_submitted_users:
            not_submitted_users_message += f"{user}\n"
        not_submitted_users_message += "```"

        summaries_message = "\n\n*Summaries:*\n"
        summaries_message += "```"
        for date, messages in categorized_data.items():
            summaries_message += f"\n*Date: {date}*\n"
            for item in messages:
                summaries_message += f"{item['user']}:\n{item['summary']}\n\n"
        summaries_message += "```"

        slack_message = f"{header_message}\n{submitted_users_message}\n{not_submitted_users_message}\n{summaries_message}"

        channel_id = "C07DT2TQDDJ"  # Replace with your destination channel ID C07CBL4DE30
        response = slack_client.chat_postMessage(channel=channel_id, text=slack_message)

        if response["ok"]:
            print(f"Data sent to channel {channel_id} on Slack.")
        else:
            print(f"Failed to send message to channel {channel_id}: {response['error']}")

    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")
    except Exception as e:
        print(f"Unexpected error: {e}")

@functions_framework.http
def slack_smart_goals(request):
    try:
        channel_id = 'C057AFRT9SN'
        messages = extract_messages(channel_id)
        if messages:
            categorized_data = process_messages(messages)
            if categorized_data:
                save_to_csv(categorized_data)
                send_slack_message(categorized_data)
            else:
                print("No messages processed.")
        else:
            print("No messages fetched from Slack.")
        return 'OK'
    except Exception as e:
        print(f"Exception occurred: {e}")
        return str(e)

if __name__ == "__main__":
    slack_smart_goals(None)
