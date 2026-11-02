
from llm_service import generate_answer

question = "Hello, can you introduce yourself?"

try:
    answer = generate_answer(question)
    print("\nGroq response:")
    print(answer)

except Exception as error:
    print("\nGroq connection failed:")
    print(type(error).__name__, str(error))
