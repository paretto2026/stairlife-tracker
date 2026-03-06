from flask import Flask

from models.database import init_db
from routes.main_routes import main_bp


app = Flask(__name__)
app.register_blueprint(main_bp)

init_db()


if __name__ == "__main__":
    app.run(debug=True)
