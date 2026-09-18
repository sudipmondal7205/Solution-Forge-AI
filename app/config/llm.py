import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv(override=True)

COHERE_API_KEY = os.getenv("COHERE_API_KEY")


if not COHERE_API_KEY:
    raise EnvironmentError("COHERE_API_KEY is not set in environment variables.")

llm = LLM(
    model="cohere/command-a-03-2025",
    api_key=COHERE_API_KEY,
    temperature=0.2,
    additional_drop_params=["strict"],
)

