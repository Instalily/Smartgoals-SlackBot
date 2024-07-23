gcloud functions deploy slack_smart_goals \
    --runtime python311 \
    --trigger-http \
    --no-allow-unauthenticated \
    --source .