

client<llm> Groq {
  provider openai-generic
  options {
    base_url "https://api.groq.com/openai/v1"
    model "llama-3.3-70b-versatile"
    api_key env.GROQ_API_KEY
  }
}

client Gemini {
  provider google-ai
  options {
    model "gemini-2.5-flash"
    api_key env.GEMINI_API_KEY
  }
}

generator target {
  output_type "python/pydantic"
  output_dir "../../auth_platform"
  version "0.216.0"
}
