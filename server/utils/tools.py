from langchain_core.tools import tool
from utils.generate_chain import create_generate_chain
import random

@tool
def fake_weather_api(city: str) -> str:
    """
    A fake weather API that returns the weather of a city.

    Args:
        city (str): The city for which to get the weather.

    Returns:
        str: The weather of the city.
    """
    if random.random() < 0.5:
        return f"The weather in {city} is sunny."
    else:
        return f"The weather in {city} is rainy."

@tool
def generate(data_type: str) -> str:
    """
    A fake generator function that simulates data generation from Infura docs.

    Args:
        data_type (str): The type of data to generate.

    Returns:
        str: A fake data generation message.
    """
    return f"Generated fake data for {data_type} from Infura docs."