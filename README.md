# Discord Bot with API Integration

This project is a Discord bot that integrates with an external API to provide answers to user questions and fetch user information.

For better service, please visit https://openonion.ai.
you can install the bot using link https://discord.com/oauth2/authorize?client_id=1274612373340164107

## Features

- Automatically detects and responds to user questions in Discord channels.
- Fetches and logs user information from an external API.

## Setup

### Prerequisites

- Python 3.7+
- A Discord bot token
- An API URL and token

### Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/openonion/OnionPal.git
   cd OnionPal
   ```

2. Create a virtual environment and activate it:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```sh
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory of the project and add your
   configuration variables:

   ```env
   DISCORD_TOKEN=your_discord_token
   API_URL=https://api.trustonion.com
   API_TOKEN=Your account token for openonion
   ```

### Running the Bot

1. Start the bot:

   ```sh
   python bot.py
   ```

## Project Structure

- `bot.py`: Main bot file that handles Discord events and commands.
- `api_client.py`: Contains functions to interact with the external API.
- `config.py`: Loads environment variables from the `.env` file.
- `question_detector.py`: Contains logic to detect if a message is a question.
- `requirements.txt`: Lists the dependencies required for the project.

## Usage

- The bot automatically detects and responds to messages that are questions.
- Use the `!ask` command followed by your question to get an answer from the
  bot.

## Example
