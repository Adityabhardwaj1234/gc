import asyncio
from pydantic import BaseModel
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.sessions import Session
from google.genai import types

import os
from dotenv import load_dotenv

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from callback_logging import log_query_to_model, log_model_response
import google.cloud.logging


# Load environment variables
load_dotenv()

google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION")
google_genai_use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()


# Define the output schema
class CountryCapital(BaseModel):
    capital: str


async def main():

    app_name = 'geo_validator_app'
    user_id_1 = 'user1'

    # Define the agent
    root_agent = Agent(
        model="gemini-3.5-flash",
        name="geo_validator",
        instruction="Answer questions about country capitals.",
        output_schema=CountryCapital,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
        before_model_callback=log_query_to_model,
        after_model_callback=log_model_response,
    )

    # Create a Runner
    runner = InMemoryRunner(
        agent=root_agent,
        app_name=app_name,
    )

    # Create a session
    my_session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id_1
    )

    # Run a prompt
    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=new_message)]
        )

        print('** User says:', content.model_dump(exclude_none=True))

        async for event in runner.run_async(
            user_id=user_id_1,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                if event.content.parts[0].text:
                    print(f'** {event.author}: {event.content.parts[0].text}')

        cloud_logging_client.close()

    query = "What is the capital of France?"
    await run_prompt(my_session, query)


if __name__ == "__main__":
    asyncio.run(main())