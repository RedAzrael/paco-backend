from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Enable CORS for all routes to allow React frontend to connect
CORS(app)

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
def get_relics():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id, name FROM relics')
            relics = cursor.fetchall()
            return jsonify(relics), 200
        except Error as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/search', methods=['GET'])
def search_relics():
    """
    Search endpoint compatible with the React frontend.
    Expects a 'q' query parameter with the search term.
    """
    search_query = request.args.get('q', '').strip()

    if not search_query:
        return jsonify({'error': 'No search query provided'}), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Search for relics where name contains the search query (case-insensitive)
            sql_query = """
            SELECT DISTINCT
                r.id AS id,
                r.name AS name,
            FROM
                relics r
                LEFT JOIN items i1 ON r.common1 = i1.id
                LEFT JOIN items i2 ON r.common2 = i2.id
                LEFT JOIN items i3 ON r.common3 = i3.id
                LEFT JOIN items i4 ON r.uncommon1 = i4.id
                LEFT JOIN items i5 ON r.uncommon2 = i5.id
                LEFT JOIN items i6 ON r.rare = i6.id
            WHERE
                r.name LIKE '%s'
                OR i1.name LIKE '%s'
                OR i1.description LIKE '%s'
                OR i2.name LIKE '%s'
                OR i2.description LIKE '%s'
                OR i3.name LIKE '%s'
                OR i3.description LIKE '%s'
                OR i4.name LIKE '%s'
                OR i4.description LIKE '%s'
                OR i5.name LIKE '%s'
                OR i5.description LIKE '%s'
                OR i6.name LIKE '%s'
                OR i6.description LIKE '%s';
                """
            search_param = f"%{search_query}%"

            cursor.execute(sql_query, (search_param,))
            results = cursor.fetchall()

            # Format results for frontend consumption
            formatted_results = []
            for relic in results:
                formatted_results.append({
                    'id': relic['id'],
                    'title': relic['name'],
                    'description': f"Relic ID: {relic['id']}"
                })

            return jsonify({
                'results': formatted_results,
                'total_count': len(formatted_results),
                'search_query': search_query
            }), 200

        except Error as e:
            print(f"Database error: {e}")
            return jsonify({'error': 'Database query failed'}), 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/search/advanced', methods=['GET'])
def advanced_search():
    """
    Advanced search endpoint that searches multiple fields if your database has them.
    This is an example of how you could extend the search functionality.
    """
    search_query = request.args.get('q', '').strip()
    search_field = request.args.get('field', 'name')  # Default to searching by name

    if not search_query:
        return jsonify({'error': 'No search query provided'}), 400

    # Validate search field to prevent SQL injection
    allowed_fields = ['id', 'name']
    if search_field not in allowed_fields:
        search_field = 'name'

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Dynamic query based on field
            if search_field == 'id':
                # Exact match for ID search
                sql_query = f"SELECT id, name FROM relics WHERE {search_field} = %s ORDER BY name"
                cursor.execute(sql_query, (search_query,))
            else:
                # Partial match for text fields
                sql_query = f"SELECT id, name FROM relics WHERE {search_field} LIKE %s ORDER BY name"
                search_param = f"%{search_query}%"
                cursor.execute(sql_query, (search_param,))

            results = cursor.fetchall()

            # Format results
            formatted_results = []
            for relic in results:
                formatted_results.append({
                    'id': relic['id'],
                    'title': relic['name'],
                    'description': f"Relic ID: {relic['id']}",
                    'search_field': search_field
                })

            return jsonify({
                'results': formatted_results,
                'total_count': len(formatted_results),
                'search_query': search_query,
                'search_field': search_field
            }), 200

        except Error as e:
            print(f"Database error: {e}")
            return jsonify({'error': 'Database query failed'}), 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return jsonify({
        'status': 'healthy',
        'message': 'Warframe Relic Search API is running',
        'endpoints': {
            'search': '/api/search?q=search_term',
            'advanced_search': '/api/search/advanced?q=search_term&field=name',
            'all_relics': '/relics'
        }
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Warframe Relic Search API...")
    print("Available endpoints:")
    print("- GET /api/search?q=<search_term> - Search relics")
    print("- GET /api/search/advanced?q=<search_term>&field=<field> - Advanced search")
    print("- GET /relics - Get all relics")
    print("- GET /api/health - Health check")

    app.run(debug=True, host='0.0.0.0', port=3001)
