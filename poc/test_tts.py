import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))

try:
    print("Testing standard English")
    res = client.text_to_speech.convert(
        text="Hello there this is a test.",
        target_language_code="en-IN",
        pace=1.1,
        speaker="simran",
        model="bulbul:v3"
    )
    print("Success 1!")
except Exception as e:
    print("Error 1:", e)

try:
    print("Testing empty text")
    res = client.text_to_speech.convert(text="", target_language_code="en-IN", model="bulbul:v3", speaker="simran")
    print("Success 2!")
except Exception as e:
    print("Error 2:", e)

