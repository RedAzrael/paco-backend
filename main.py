from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import mysql.connector
from mysql.connector import Error
from os import environ

app = Flask(__name__)

# Enable CORS for all routes to allow React frontend to connect
cors = CORS(app)

# MySQL configuration
db_config = {
    'host': 'db',
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
            sql_query = sql_query = """
            SELECT DISTINCT
                r.id AS id,
                r.name AS name
            FROM
                relics r
                 LEFT JOIN items i1 ON r.common1 = i1.id
                 LEFT JOIN items i2 ON r.common2 = i2.id
                 LEFT JOIN items i3 ON r.common3 = i3.id
                 LEFT JOIN items i4 ON r.uncommon1 = i4.id
                 LEFT JOIN items i5 ON r.uncommon2 = i5.id
                 LEFT JOIN items i6 ON r.rare = i6.id
            WHERE
                r.name LIKE %s
                OR i1.name LIKE %s
                OR i1.description LIKE %s
                OR i2.name LIKE %s
                OR i2.description LIKE %s
                OR i3.name LIKE %s
                OR i3.description LIKE %s
                OR i4.name LIKE %s
                OR i4.description LIKE %s
                OR i5.name LIKE %s
                OR i5.description LIKE %s
                OR i6.name LIKE %s
                OR i6.description LIKE %s;
                """
            search_param = f"%{search_query}%"

            cursor.execute(sql_query, (search_param,) * 13)
            results = cursor.fetchall()

            # Format results for frontend consumption with detailed information
            formatted_results = []
            for relic in results:
                # Get detailed relic information including items
                relic_cursor = conn.cursor(dictionary=True)
                detailed_query = """
                SELECT
                    r.id AS relic_id,
                    r.name AS relic_name,
                    i1.name AS common1_name,
                    i2.name AS common2_name,
                    i3.name AS common3_name,
                    i4.name AS uncommon1_name,
                    i5.name AS uncommon2_name,
                    i6.name AS rare_name
                FROM relics r
                LEFT JOIN items i1 ON r.common1 = i1.id
                LEFT JOIN items i2 ON r.common2 = i2.id
                LEFT JOIN items i3 ON r.common3 = i3.id
                LEFT JOIN items i4 ON r.uncommon1 = i4.id
                LEFT JOIN items i5 ON r.uncommon2 = i5.id
                LEFT JOIN items i6 ON r.rare = i6.id
                WHERE r.id = %s
                """
                relic_cursor.execute(detailed_query, (relic['id'],))
                relic_details = relic_cursor.fetchone()
                relic_cursor.close()

                if relic_details:
                    # Check if search matched relic name
                    relic_name_match = search_query.lower() in relic['name'].lower()

                    # Check if search matched any item name
                    item_matches = []
                    items_info = [
                        (relic_details['common1_name'], 'Common'),
                        (relic_details['common2_name'], 'Common'),
                        (relic_details['common3_name'], 'Common'),
                        (relic_details['uncommon1_name'], 'Uncommon'),
                        (relic_details['uncommon2_name'], 'Uncommon'),
                        (relic_details['rare_name'], 'Rare')
                    ]

                    for item_name, rarity in items_info:
                        if item_name and search_query.lower() in item_name.lower():
                            item_matches.append((item_name, rarity))

                    # Format description based on what was matched
                    if relic_name_match:
                        # Search included relic name - show relic and all its items with rarities
                        description_parts = [f"Relic: {relic['name']}"]
                        description_parts.append("Items:")
                        for item_name, rarity in items_info:
                            if item_name:  # Only show items that exist
                                description_parts.append(f"• {item_name} ({rarity})")
                        description = "\n".join(description_parts)
                    elif item_matches:
                        # Search included item name - show relic name and matched item with rarity
                        description_parts = [f"Relic: {relic['name']}"]
                        description_parts.append("Matched Items:")
                        for item_name, rarity in item_matches:
                            description_parts.append(f"• {item_name} ({rarity})")
                        description = "\n".join(description_parts)
                    else:
                        # Fallback - shouldn't happen with the current query but just in case
                        description = f"Relic: {relic['name']} (ID: {relic['id']})"

                    formatted_results.append({
                        'id': relic['id'],
                        'title': relic['name'],
                        'description': description
                    })
                else:
                    # Fallback if detailed query fails
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
    print("Internal error occured")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Warframe Relic Search API...")
    print("Available endpoints:")
    print("- GET /api/search?q=<search_term> - Search relics")
    print("- GET /api/search/advanced?q=<search_term>&field=<field> - Advanced search")
    print("- GET /relics - Get all relics")
    print("- GET /api/health - Health check")
    app.run(debug=True, host='0.0.0.0', port=3001)
