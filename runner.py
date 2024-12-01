from app import create_app

if __name__ == '__main__':
    app = create_app()
    ssl_context = ('cert.pem', 'key.pem')
    app.run(debug=True, ssl_context=ssl_context)
