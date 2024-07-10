from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from datetime import datetime, timedelta
import csv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import openai
import uvicorn
from dotenv import load_dotenv

load_dotenv()

slack_token = os.getenv('SLACK_API_TOKEN')
openai_api_key = os.getenv('OPENAI_API_KEY')



client = WebClient(token=slack_token)

specific_users = ["Cristin Connerney", "Logan Ge", "Dhiraj Khanal", "Iris Cheng", "Mateo Godoy", "Hongyi Wu", "Prashanthi Ramachandran", "Morgann Thain", "Joshua Shou", "Geneva", 
                  "Sujit Varadhan", "Laryn Qi", "Edward Kim", "Sriyans Rauniyar", "Zubin Chandra", "Doris Huang", "Alex Kim", "Mars Tan", "Aris Zhu", "Brigit Jacob", "Jack Rangaiah", "Roey Abehsera"] # list of every user currently part of instalilly

def get_user_name(user_id):   # real name instead of user id
    result = client.users_info(user=user_id)
    return result['user']['real_name']

def extract_messages(channel_id): # extrscting the info from slack
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24) # extracs the last 24 hours of text
        

        oldest_time = int(start_time.timestamp())
        latest_time = int(end_time.timestamp())

        result = client.conversations_history(
            channel=channel_id,
            oldest=oldest_time,
            latest=latest_time
        )
        return result['messages'] 
    except SlackApiError as e:     # very important trouble shooting 
        if e.response['error'] == 'channel_not_found':
            print(f"Error: Channel '{channel_id}' not found. it could me the ID is incorrect of there arnt enough permissions granted to the bot.")
        elif e.response['error'] == 'invalid_auth':
            print("Error: Invalid authentication token. check if the Slack API token is the right one.")
        elif e.response['error'] == 'token_revoked':
            print("Error: Token revoked. go make a new token")
        else:
            print(f"Error fetching messages: {e.response['error']}")
    return []

def process_messages(messages): # going through the information collected from slack
    processed_data = []
    for msg in messages:
        user = msg.get('user')
        if user:
            username = get_user_name(user)
            if username and username in specific_users:
                submitted_users.add(username)
                not_submitted_users.discard(username) # originally all names are placed in not submitted and this transfers the submitted ones to submitted 
                timestamp = datetime.fromtimestamp(float(msg['ts']))
                text = msg['text']
                summary = generate_summary(text)
                processed_data.append({
                    'user': username,
                    'timestamp': timestamp,
                    'text': text,
                    'summary': summary
                })
    return processed_data

def generate_summary(text): # Using GPT to make a summary of the message
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "system", "content": "You are a helpful assistant, summarizing today's work completed by each person for their boss in a very short and concise way."},
            {"role": "user", "content": text}
        ],
    )
    return response.choices[0]['message']['content'].strip()

def main(): # extracting the messages from slack
    global submitted_users, not_submitted_users
    submitted_users = set() # resets names
    not_submitted_users = set(specific_users) # preplaces everyone in the did not submit catagory

    channel_id = 'C057AFRT9SN'  # The ID for the specific slack channel im extracting from
    messages = extract_messages(channel_id)
    if messages:
        processed_data = process_messages(messages)
        if processed_data:
            save_to_csv(processed_data)
        else:
            print("No messages sent.")
    else:
        print("No messages fetched from Slack.")

def save_to_csv(data): # sending info to CSV file
    csv_filename = 'C:/Users/Cubico/Desktop/slack_smart_goals.csv' # My CVS file name
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'date', 'summary']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)


            csvfile.write("Submitted Users:\n") # list submitted
            for user in submitted_users:
                csvfile.write(f"{user} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            csvfile.write("\n")
            


            csvfile.write("Not Submitted Users:\n") # list nonsubmitted
            for user in not_submitted_users:
                csvfile.write(f"{user}\n")
            csvfile.write("\n")



            writer.writeheader()
            for item in data:
                writer.writerow({
                    'name': item['user'],
                    'date': item['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': item['summary']
                })
        print(f"Data saved to {os.path.abspath(csv_filename)}")
    except IOError as e:
        print(f"Error saving to CSV: {e}")

# the times it'll run
scheduler = BackgroundScheduler()
scheduler.add_job(main, CronTrigger(hour='16', minute='15', second='0'))  # 11pm
scheduler.start()



app = FastAPI()

@app.get("/")
def get_status():
    return {"status": "Running"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)