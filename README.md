## Running with Docker

Alternatively, you can run the application using Docker.

1.  **Build the Docker image:**
    ```bash
    docker build -t allergoproba .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:8000 --env-file .env allergoproba
    ```

The application will be available at `http://127.0.0.1:8000`.



## Alternative: Running Locally

1. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2. **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file** by copying the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** and add your Telegram Bot Token and a default chat ID:
    ```env
    TELEGRAM_BOT_TOKEN="Telegram_bot_id_is_set_on_env.example"
    TELEGRAM_DEFAULT_CHAT_ID="your_telegram_chat_id"
    ```
    - `TELEGRAM_BOT_TOKEN`: Already on .env.example.
    - `TELEGRAM_DEFAULT_CHAT_ID`: A chat ID to send notifications. You can get your chat ID by @Getmyid_bot

## Running the Application

To run the web server, use `uvicorn`:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at `http://127.0.0.1:8000`.

## Usage

-   **Dentist's Interface**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
-   **Laboratory Interface**: [http://127.0.0.1:8000/lab](http://127.0.0.1:8000/lab)