from google import genai

client = genai.Client(api_key="AIzaSyDFS7kQUM3hmxjmWjQjwdbGbcauvjeOqFI")
chat = client.chats.create(model="gemini-2.0-flash")

response = chat.send_message("Hello world!")
print(response.text)

response = chat.send_message("Explain to me how AI works")
print(response.text)

for message in chat.get_history():
    print(f'role - {message.role}',end=": ")
    print(message.parts[0].text)