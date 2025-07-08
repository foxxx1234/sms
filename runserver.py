from FreeSMS import app
if __name__ == "__main__":
    import os
    host = os.environ.get("SERVER_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("SERVER_PORT", "5555"))
    except ValueError:
        port = 5555
    app.run(host=host, port=port, debug=True)
