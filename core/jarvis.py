import asyncio
import speech_recognition as sr
import pyttsx3
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
import sys

# Initialize Text-to-Speech (The Voice of Jarvis)
engine = pyttsx3.init()
engine.setProperty('rate', 170) # Speed of speech
voices = engine.getProperty('voices')
# Optional: Try to set to a male voice for a more "Jarvis" feel
for voice in voices:
    if "david" in voice.name.lower() or "male" in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

def speak(text):
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()

import sounddevice as sd
import scipy.io.wavfile as wav
import os

# Listen to microphone (Speech-to-Text) using sounddevice
def listen():
    fs = 44100  # Sample rate
    duration = 5  # seconds
    print("\n[!] Listening for your command for 5 seconds...")
    try:
        # Record audio
        myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()  # Wait until recording is finished
        wav.write('temp.wav', fs, myrecording)  # Save as WAV file 
    except Exception as e:
        print(f"Error recording audio: {e}")
        return None
    
    # Process audio
    recognizer = sr.Recognizer()
    with sr.AudioFile('temp.wav') as source:
        audio = recognizer.record(source)
        
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None

async def main():
    # Ensure the API key is set
    if not os.environ.get("GEMINI_API_KEY"):
        print("="*60)
        print("Missing Gemini API Key!")
        print("You can get a FREE API key from: https://aistudio.google.com/app/apikey")
        print("="*60)
        api_key = input("Please paste your Gemini API Key here: ").strip()
        os.environ["GEMINI_API_KEY"] = api_key
        print("API Key saved for this session!\n")

    # Configure Antigravity to act like Jarvis and give it permission to use tools
    config = LocalAgentConfig(
        system_instructions="You are Jarvis, a highly capable AI assistant. Keep your verbal responses concise and conversational while executing actions in the background. Never output markdown formatting or bullet points since your response will be read aloud by a text-to-speech engine. Just speak naturally.",
        capabilities=CapabilitiesConfig() # Gives the agent power to run commands, edit files, etc.
    )

    speak("System online. Antigravity backend initialized. Waiting for commands.")

    # Spawn the Antigravity agent
    async with Agent(config) as agent:
        while True:
            # 1. Listen to user
            command = listen()
            
            if command:
                if "shutdown" in command.lower() or "stop listening" in command.lower():
                    speak("Shutting down sir.")
                    break
                
                # 2. Send command to Antigravity Agent
                print("[*] Processing command...")
                response_stream = await agent.chat(command)
                
                # 3. Collect the text response from the agent
                full_response = ""
                async for token in response_stream:
                    full_response += token
                
                # 4. Speak the response out loud
                speak(full_response)
            
            # small sleep to prevent CPU hogging
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
        sys.exit(0)
