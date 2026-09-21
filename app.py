import os
from flask import Flask, redirect, url_for
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app()
    
    # Register Blueprints
    from routes_auth import auth_bp
    from routes_ops import ops_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(ops_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('ops.dashboard'))
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
