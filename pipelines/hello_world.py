import time
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field

class Pipeline:
    class Valves(BaseModel):
        FOO: str = Field(default="bar")

    def __init__(self):
        self.name = "Hello World pipeline"
        self.valves = self.Valves()

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup: {__name__}")

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown: {__name__}")

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe: {__name__}")
        print(f"user_message: {user_message}") # Contient le dernier message de l'utilisateur, par exemple `Message 3`

        print("messages:")
        print(messages)
        # messages contains the conversation history, example:
        # [
        #    {'role': 'user', 'content': 'Message 1'},
        #    {'role': 'assistant', 'content': 'Hello world'},
        #    {'role': 'user', 'content': 'Message 2'},
        #    {'role': 'assistant', 'content': 'Hello world'},
        #    {'role': 'user', 'content': 'Message 3'}
        # ]

        print("body:")
        print(body)
        # example:
        # {
        #     'stream': True,
        #     'model': 'hello_world',
        #     'messages': [
        #         {'role': 'user', 'content': 'Message 1'},
        #         {'role': 'assistant', 'content': 'Hello world'},
        #         {'role': 'user', 'content': 'Message 2'},
        #         {'role': 'assistant', 'content': 'Hello world'},
        #         {'role': 'user', 'content': 'Message 3'}
        #     ],
        #     'user': {
        #         'name': 'stephane-klein',
        #         'id': '3aaa0156-3181-403b-bcbd-6047a2988a9d',
        #         'email': 'contact@stephane-klein.info',
        #         'role': 'admin'
        #     }
        # }

        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "I thinking",
                    "done": False,
                },
            }
        }

        time.sleep(2)

        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "Ok, I found it!",
                    "done": False,
                },
            }
        }

        time.sleep(1)

        yield f"""
            Hello world 2

            You said « {user_message} » !

            Valve foo value: {self.valves.FOO}
        """

        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": "",
                    "done": True,
                },
            }
        }
