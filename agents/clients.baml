
client<llm> Gemini {
  provider google-ai
  options {
    model "gemini-1.5-pro-002"
    api_key env.API_KEY
  }
}
