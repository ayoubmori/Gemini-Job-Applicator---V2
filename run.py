from app import create_app

app = create_app()

if __name__ == '__main__':
    # Make sure to place your credentials.json in the root directory
    app.run(debug=True)