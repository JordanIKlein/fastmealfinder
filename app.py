from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from psycopg2.extras import RealDictCursor
from datetime import timedelta
from pool_connection import DatabasePoolConnection
import math
import os
import logging
import traceback


app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)
# Set session lifetime to (for example) 15 minutes of inactivity.
app.config['SESSION_TYPE'] = None
#app.permanent_session_lifetime = timedelta(minutes=15)
#app.config['SESSION_TYPE'] = 'filesystem'  # Store session on the server
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000


# Your Firebase Web API Key (from your Firebase project settings)
# Create a single global connection pool at app level
db_connection = DatabasePoolConnection()
# Helper functions (not endpoints) that return data from the DB
def fetch_companies():
    with db_connection.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = "SELECT DISTINCT companyid, companyname, deallink FROM companies WHERE deallink IS NOT NULL AND deallink <> '' ORDER BY companyname;"
            cursor.execute(query)
            companies = cursor.fetchall()
    
    # Ensure image paths match expected static file names
    for company in companies:
        company["image_url"] = f"/static/{company['companyid']}.png"  # Assuming all images are .png
    return companies


def fetch_cuisines():
    with db_connection.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = "SELECT DISTINCT type FROM companies ORDER BY type;"
            cursor.execute(query)
            cuisines = cursor.fetchall()
    return cuisines

def get_locations_from_db(
    south_west_lng=-124.848974, south_west_lat=24.396308,
    north_east_lng=-66.93457,   north_east_lat=49.384358
):
    try:
        with db_connection.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT l.locationid,
                           l.latitude,
                           l.longitude,
                           l.address,
                           l.city,
                           l.state,
                           l.zipcode,
                           l.housenumber,
                           l.street,
                           l.hours,
                           c.companyname,
                           c.companyid,
                           c.type AS cuisine_type
                    FROM locations l
                    JOIN companies c ON l.companyid = c.companyid
                    WHERE l.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                    ORDER BY
                      ST_Distance(
                        l.geom,
                        ST_Centroid(
                          ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                        )
                      ) + (random() * 50)
                    LIMIT 100;
                """
                # **EIGHT** parameters now, matching the eight %s above
                params = (
                    south_west_lng, south_west_lat, north_east_lng, north_east_lat,
                    south_west_lng, south_west_lat, north_east_lng, north_east_lat
                )
                cur.execute(query, params)
                results = cur.fetchall()
        print("Results:", results)  # Debugging
        def sanitize_value(val):
            if isinstance(val, float) and math.isnan(val):
                return None
            return val
        # inside your loop:
        results = [
            {k: sanitize_value(v) for k, v in row.items()}
            for row in cur.fetchall()
        ]
        return results
    except Exception as e:
        print(f"Error: {e}")
        return []

    except Exception as e:
        print(f"Error: {e}")
        return []
# The explore route now simply passes the initial locations (using the default bounding box).
@app.route('/')
@app.route('/explore')
def explore():
    locations = get_locations_from_db()
    return render_template('explore.html', locations=locations)

# Endpoint versions of the helper functions (if needed)
@app.route('/get_companies', methods=['GET'])
def get_companies_endpoint():
    companies = fetch_companies()
    return jsonify(companies)

@app.route('/get_cuisines', methods=['GET'])
def get_cuisines_endpoint():
    cuisines = fetch_cuisines()
    return jsonify(cuisines)

# An endpoint that returns both companies and cuisines for your JS filters
@app.route('/get_companies_and_cuisines', methods=['GET'])
def get_companies_and_cuisines():
    try:
        companies = fetch_companies()
        cuisines = fetch_cuisines()
        return jsonify({"companies": companies, "cuisines": cuisines})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# An endpoint to get locations by bounding box (if you need it separately)
@app.route('/locations', methods=['GET'])
def get_locations():
    south_west_lng = request.args.get('southWestLng', type=float)
    south_west_lat = request.args.get('southWestLat', type=float)
    north_east_lng = request.args.get('northEastLng', type=float)
    north_east_lat = request.args.get('northEastLat', type=float)
    if None in (south_west_lng, south_west_lat, north_east_lng, north_east_lat):
        return jsonify({"error": "Missing bounding box parameters"}), 400
    try:
        with db_connection.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT l.locationid,
                           l.latitude,
                           l.longitude,
                           l.address,
                           l.city,
                           l.state,
                           l.zipcode,
                           l.housenumber,
                           l.street,
                           l.hours,
                           c.companyname,
                           c.companyid,
                           c.type as cuisine_type
                    FROM locations l
                    JOIN companies c ON l.companyid = c.companyid
                    WHERE l.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                    LIMIT 100;
                """
                cur.execute(query, (south_west_lng, south_west_lat, north_east_lng, north_east_lat))
                locations = cur.fetchall()
        return jsonify(locations)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# This endpoint accepts optional filtering for companies and cuisines.
@app.route('/get_filtered_locations', methods=['GET'])
def get_filtered_locations():
    company_filter = request.args.getlist('company[]')
    cuisine_filter = request.args.getlist('cuisine[]')
    south_west_lng = request.args.get('southWestLng', type=float)
    south_west_lat = request.args.get('southWestLat', type=float)
    north_east_lng = request.args.get('northEastLng', type=float)
    north_east_lat = request.args.get('northEastLat', type=float)
    
    if None in (south_west_lng, south_west_lat, north_east_lng, north_east_lat):
        return jsonify({"error": "Missing bounding box parameters"}), 400

    query = """
        SELECT l.locationid,
               l.latitude,
               l.longitude,
               l.address,
               l.city,
               l.state,
               l.zipcode,
               l.housenumber,
               l.street,
               l.hours,
               c.companyname,
               c.companyid,
               c.type as cuisine_type
        FROM locations l
        JOIN companies c ON l.companyid = c.companyid
        WHERE l.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
    """
    params = [south_west_lng, south_west_lat, north_east_lng, north_east_lat]

    if company_filter:
        query += " AND c.companyname = ANY(%s)"
        params.append(company_filter)
    if cuisine_filter:
        query += " AND c.type = ANY(%s)"
        params.append(cuisine_filter)
    
    query += " LIMIT 100;"

    try:
        with db_connection.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(params))
                locations = cur.fetchall()
        return jsonify(locations)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

    
   
# 📌 Autocomplete API - Returns matching towns, ZIP codes, etc.
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    try:
        with db_connection.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:  # Use column names, not indexes
                sql = """
                    SELECT city_name, zip_code, state_name, ST_X(geo_point) AS lon, ST_Y(geo_point) AS lat
                    FROM us_locations
                    WHERE LOWER(city_name) LIKE %s OR zip_code LIKE %s
                    LIMIT 10;
                """
                cursor.execute(sql, (f"%{query}%", f"%{query}%"))
                results = cursor.fetchall()

                print("Results:", results)  # Debugging

        return jsonify([
            {
                "city": row["city_name"],  # Use column names instead of indexes
                "zip": row["zip_code"],
                "state": row["state_name"],
                "lon": row["lon"],  # Longitude
                "lat": row["lat"]   # Latitude
            } for row in results
        ])

    except Exception as e:
        logging.error("ERROR: %s", traceback.format_exc())  # Log detailed error message
        return jsonify({"error": "An internal error has occurred!"}), 500

@app.route('/search', methods=['GET'])
def search():
    location = request.args.get('q', '').strip().lower()
    if not location:
        return jsonify({"error": "No location provided"}), 400

    with db_connection.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Use ILIKE for case-insensitive, partial matching
            sql = """
                SELECT city_name, zip_code, state_name, ST_X(geo_point), ST_Y(geo_point)
                FROM us_locations
                WHERE city_name ILIKE %s OR zip_code ILIKE %s
                LIMIT 1;
            """
            # Match the location with the city name or zip code, with partial matching
            cursor.execute(sql, (f"%{location}%", f"%{location}%"))
            result = cursor.fetchone()

            # Debugging output
            print(f"Search query: {location}")
            print("Search result:", result)

            if result:
                return jsonify({
                    "city": result["city_name"],  # Ensure you're accessing the dictionary key correctly
                    "zip": result["zip_code"],
                    "state": result["state_name"],
                    "lon": result["st_x"],  # Longitude
                    "lat": result["st_y"]   # Latitude
                })
            else:
                return jsonify({"error": "Location not found"}), 404

@app.route('/deals')
def deals():
    return render_template('deals.html')

@app.route('/get_companies', methods=['GET'])
def get_companies():
    with db_connection.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = "SELECT DISTINCT companyid, companyname FROM companies ORDER BY companyname;"
            cursor.execute(query)
            companies = cursor.fetchall()
    return jsonify(companies)

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    response = send_from_directory(os.path.join(app.root_path, 'static'), filename)
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 1 day
    return response

if __name__ == '__main__':
    #app.run(debug=True, host='127.0.0.1', port=3000)
    app.run(debug=False, host='0.0.0.0', port=3000)