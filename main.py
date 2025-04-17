import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()
app = Flask(__name__)

# ENV variables
AIRTABLE_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


# Health check route
@app.route("/", methods=["GET"])
def index():
    return "GlossBot is running!"


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    ig_handle = data.get("instagram_handle")
    user_message = data.get("message")

    if not ig_handle or not user_message:
        return jsonify({"error": "Missing instagram_handle or message"}), 400

    # Step 1: Fetch business info from Airtable
    headers = {"Authorization": f"Bearer {AIRTABLE_KEY}"}
    params = {"filterByFormula": f"{{Instagram Handle}} = '{ig_handle}'"}
    airtable_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    r = requests.get(airtable_url, headers=headers, params=params)
    results = r.json()

    if not results.get("records"):
        return jsonify({
            "reply":
            "Hey babe! I’m not sure who this is — let me check and get back to you asap 💕"
        }), 200

    record = results["records"][0]["fields"]

    # Step 2: Format the GPT prompt
    prompt = f"""
You are GlossBot — an AI sales assistant working for a beauty service provider named {record.get('Name')}.

Your job is to respond to Instagram DMs in a way that matches the business’s selected tone: {record.get('Tone Style')}. Only use information provided by the business. Do not make up anything.

Here is the business information:

- Services & Prices: {record.get('Services & Prices')}
- Booking Link: {record.get('Booking Link')}
- Business Hours: {record.get('Business Hours')}
- Location: {record.get('Location')}
- Cancellation Policy: {record.get('Cancellation Policy')}
- Tone Style: {record.get('Tone Style')}
- Sign-Off Emoji: {record.get('Sign-Off Emoji')}
- FAQs: {record.get('Custom FAQs')}

When someone sends a message like “How much for a lash lift?” or “Are you open Friday?”, use the info above to answer in the {record.get('Tone Style')} voice. Always include the {record.get('Sign-Off Emoji')} at the end of every message.

Be friendly, fast, and make it easy for them to book.

If the question isn't covered in the data, respond with:
“Hey babe! I’m not sure about that — let me check and get back to you asap {record.get('Sign-Off Emoji')}”

Do not mention you are an AI. You are a friendly assistant.

Now reply to this message:
**{user_message}**
    """

    # Step 3: Call GPT-3.5 or GPT-4
    gpt_headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "gpt-3.5-turbo",
        "messages": [{
            "role": "user",
            "content": prompt
        }],
        "temperature": 0.7
    }

    gpt_response = requests.post("https://api.openai.com/v1/chat/completions",
                                 headers=gpt_headers,
                                 json=body)

    gpt_result = gpt_response.json()
    reply = gpt_result["choices"][0]["message"]["content"]

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
