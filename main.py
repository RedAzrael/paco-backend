from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# MySQL configuration
db_config = {
    'host': 'localhost',
    'user': 'warframe_user',
    'password': 'secure_password_123',
    'database': 'warframe'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/relics', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id, name FROM relics')
            users = cursor.fetchall()
            return jsonify(users), 200
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
