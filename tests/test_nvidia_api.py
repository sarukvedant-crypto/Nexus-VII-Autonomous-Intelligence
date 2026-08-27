from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

try:
    completion = client.chat.completions.create(
      model="meta/llama-3.3-70b-instruct",
      messages=[{"role":"user","content":"Hello, respond with exactly the word SUCCESS."}],
      temperature=0.2,
      top_p=0.7,
      max_tokens=1024,
      stream=False
    )
    print("API SUCCESS:", completion.choices[0].message.content)
except Exception as e:
    print("API FAILED:", e)
