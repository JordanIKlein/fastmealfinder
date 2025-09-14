from flask import Flask, jsonify, render_template, request, send_from_directory, make_response, abort
from datetime import datetime, time
import requests
import os
from werkzeug.utils import secure_filename
import re

import json
from pool_connection import DatabasePoolConnection
# Change to env variables in production.
# Load Mailchimp settings (you can use environment variables in production)
MAILCHIMP_API_KEY = os.getenv('MAILCHIMP_API_KEY')
MAILCHIMP_LIST_ID = os.getenv('MAILCHIMP_LIST_ID')
if MAILCHIMP_API_KEY:
    MAILCHIMP_DC = MAILCHIMP_API_KEY.split('-')[-1]  # Extract datacenter from API key
else:
    MAILCHIMP_DC = None
    print("Warning: MAILCHIMP_API_KEY not found in environment variables")
MAILCHIMP_API_URL = f'https://{MAILCHIMP_DC}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members'

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
db_connection = DatabasePoolConnection()

@app.context_processor
def inject_config():
    return {
        'google_analytics_id': os.getenv('GOOGLE_ANALYTICS_ID'),
    }

def safe_parse_json(val):
    """Safely parse JSON string or return the value if already parsed"""
    try:
        return json.loads(val) if isinstance(val, str) else val
    except json.JSONDecodeError:
        return {}

def convert_to_24hr(time_str):
    """Convert formats like '6am', '6:30am', '1130pm', '11:30pm', '3am' to 'HH:MM'"""
    if not time_str:
        return None
        
    time_str = time_str.strip().lower().replace(" ", "")
    
    # Handle special cases
    if time_str in ['midnight', '12am']:
        return "00:00"
    if time_str in ['noon', '12pm']:
        return "12:00"
    
    # Remove any non-alphanumeric characters except colon
    time_str = re.sub(r'[^0-9:apm]', '', time_str)
    
    # Try different parsing formats
    formats_to_try = [
        ("%I:%M%p", time_str),  # 6:30am, 11:30pm
        ("%I%p", time_str),     # 6am, 11pm
        ("%H:%M", time_str),    # 06:30, 23:30 (already 24hr)
        ("%H%M", time_str),     # 0630, 2330 (already 24hr)
    ]
    
    # Handle formats like '1130pm' -> '11:30pm'
    if len(time_str) >= 5 and time_str[-2:] in ['am', 'pm'] and ':' not in time_str:
        numeric_part = time_str[:-2]
        if len(numeric_part) == 3:  # like '630pm'
            time_str = numeric_part[0] + ':' + numeric_part[1:] + time_str[-2:]
        elif len(numeric_part) == 4:  # like '1130pm'
            time_str = numeric_part[:2] + ':' + numeric_part[2:] + time_str[-2:]
        formats_to_try.insert(0, ("%I:%M%p", time_str))
    
    for fmt, time_to_parse in formats_to_try:
        try:
            parsed_time = datetime.strptime(time_to_parse, fmt)
            return parsed_time.strftime("%H:%M")
        except ValueError:
            continue
    
    #print(f"Warning: failed to parse time '{time_str}'")
    return None

def normalize_hours(hours):
    """Normalize restaurant hours to a consistent format"""
    if not hours or not isinstance(hours, dict):
        return None

    normalized = {}
    
    for day, value in hours.items():
        day_key = day.lower()
        #print(f"Normalizing {day_key}: {value}")
        
        if not value:
            continue
            
        if isinstance(value, str):
            val = value.strip()
            
            # Handle 24-hour operations
            if val.lower() in ["open 24 hours", "24 hours", "24/7"]:
                normalized[day_key] = ["00:00", "23:59"]
                continue
            
            # Handle closed
            if val.lower() in ["closed", "close"]:
                continue
            
            # Parse time ranges like "6am - 3am" or "10:30am - 11:30pm"
            time_range_pattern = r'(\d{1,2}:?\d{0,2}\s*(?:am|pm))\s*-\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm))'
            match = re.search(time_range_pattern, val.lower())
            
            if match:
                open_time_str = match.group(1)
                close_time_str = match.group(2)
                
                open_time = convert_to_24hr(open_time_str)
                close_time = convert_to_24hr(close_time_str)
                
                if open_time and close_time:
                    normalized[day_key] = [open_time, close_time]
                else:
                    print(f"Failed to parse times for {day}: {value}")
            else:
                print(f"Could not parse time range format for {day}: {value}")
                
        elif isinstance(value, list) and len(value) == 2:
            # Already in the correct format
            normalized[day_key] = value
        else:
            print(f"Unsupported format for {day}: {value}")
    
    #print(f"Normalized hours: {normalized}")
    return normalized

def is_open_now(hours_dict):
    """Check if restaurant is currently open"""
    if not hours_dict:
        return False
    
    now = datetime.now()
    day_name = now.strftime('%A').lower()
    current_time = now.strftime('%H:%M')
    
    #print(f"Checking if open now - Day: {day_name}, Current time: {current_time}")
    
    if day_name not in hours_dict:
        print(f"No hours found for {day_name}") # Look into this! #ERROR
        return False
    
    times = hours_dict[day_name]
    if not times or len(times) != 2:
        print(f"Invalid times format for {day_name}: {times}")
        return False
    
    open_time, close_time = times
    #print(f"Restaurant hours for {day_name}: {open_time} - {close_time}")
    
    # Handle overnight closing (e.g., 6am - 3am means open until 3am next day)
    if close_time < open_time:
        # Restaurant is open from open_time to midnight, OR from midnight to close_time
        is_open = current_time >= open_time or current_time <= close_time
        #print(f"Overnight hours - Open: {is_open}")
        return is_open
    else:
        # Normal same-day hours
        is_open = open_time <= current_time <= close_time
        #print(f"Same-day hours - Open: {is_open}")
        return is_open

def is_24_hour(hours_dict):
    """Check if restaurant operates 24 hours"""
    if not hours_dict:
        return False

    # Check if all days are 24 hours or if any day is 24 hours
    for day, times in hours_dict.items():
        if not times:
            continue
        if isinstance(times, list) and len(times) == 2:
            if times == ["00:00", "23:59"]:
                return True
    return False

def is_open_late(hours_dict):
    """Check if restaurant is open late (past 9 PM or overnight)"""
    if not hours_dict:
        return False
    
    for day, times in hours_dict.items():
        if not times or len(times) != 2:
            continue
        
        open_time, close_time = times
        
        try:
            close_hour = int(close_time.split(':')[0])
            open_hour = int(open_time.split(':')[0])
            
            # Check if closes after 9 PM (21:00)
            if close_hour >= 21:
                return True
            
            # Check for overnight operation (close time is earlier than open time)
            if close_time < open_time:
                return True
                
        except (ValueError, IndexError):
            print(f"Error parsing hours for {day}: {times}")
            continue
    
    return False


@app.route("/")
def index():
    return render_template('index.html') #, google_analytics_id=os.getenv('GOOGLE_ANALYTICS_ID')

@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    data = request.json

    email = data.get('email')
    first_name = data.get('firstName', '')
    last_name = data.get('lastName', '')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    payload = {
        "email_address": email,
        "status": "subscribed",
        "merge_fields": {
            "FNAME": first_name,
            "LNAME": last_name
        }
    }

    response = requests.post(
        MAILCHIMP_API_URL,
        auth=("anystring", MAILCHIMP_API_KEY),
        json=payload
    )

    if response.status_code == 200 or response.status_code == 204:
        return jsonify({'message': 'Successfully subscribed!'}), 200
    else:
        return jsonify({'error': 'Subscription failed', 'details': response.json()}), response.status_code

@app.route("/api/restaurants")
def get_restaurants():
    # Get bounds from query parameters
    north = request.args.get('north', type=float)
    south = request.args.get('south', type=float)
    east = request.args.get('east', type=float)
    west = request.args.get('west', type=float)
    
    with db_connection.connection() as conn:
        cur = conn.cursor()
        
        # Base query
        base_query = """
            SELECT
                rl.id, rl.name, COALESCE(c.name, rl.company_id) AS company,
                rl.latitude, rl.longitude,
                rl.address, rl.city, rl.state, rl.zip,
                rl.has_drive_thru, rl.has_wifi,
                rl.has_online_ordering, rl.has_catering,
                rl.dine_in_hours, rl.drive_thru_hours,
                rl.phone_number, rl.ubereats_link, rl.doordash_link
            FROM restaurant_locations rl
            LEFT JOIN companies c ON TRIM(rl.company_id) = TRIM(c.name)
            WHERE rl.latitude IS NOT NULL 
            AND rl.longitude IS NOT NULL
            AND rl.latitude != 0 
            AND rl.longitude != 0
        """
        
        # Add bounds filtering if provided
        if all(param is not None for param in [north, south, east, west]):
            base_query += """
                AND rl.latitude BETWEEN %s AND %s
                AND rl.longitude BETWEEN %s AND %s
            """
            cur.execute(base_query, (south, north, west, east))
        else:
            cur.execute(base_query)
            
        rows = cur.fetchall()
        cur.close()

    result = []
    for row in rows:
        # Validate coordinates before processing
        latitude = row[3]
        longitude = row[4]
        
        # Skip restaurants with invalid coordinates
        if latitude is None or longitude is None:
            continue
            
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            continue
            
        # Skip restaurants with obviously invalid coordinates
        if latitude == 0 or longitude == 0:
            continue

        dine_in_hours_raw = safe_parse_json(row[13])
        drive_thru_hours_raw = safe_parse_json(row[14])
        dine_in_hours = normalize_hours(dine_in_hours_raw)
        drive_thru_hours = normalize_hours(drive_thru_hours_raw)
        
        open_now_dine_in = is_open_now(dine_in_hours)
        open_now_drive_thru = is_open_now(drive_thru_hours)

        result.append({
            "id": row[0],
            "name": row[1],
            "company": row[2],
            "latitude": latitude,
            "longitude": longitude,
            "address": row[5],
            "city": row[6],
            "state": row[7],
            "zip": row[8],
            "has_drive_thru": row[9],
            "has_wifi": row[10],
            "has_online_ordering": row[11],
            "has_catering": row[12],
            "open_now_dine_in": open_now_dine_in,
            "open_now_drive_thru": open_now_drive_thru,
            "is_24h_dine_in": is_24_hour(dine_in_hours) if dine_in_hours else False,
            "is_24h_drive_thru": is_24_hour(drive_thru_hours) if drive_thru_hours else False,
            "open_late_dine_in": is_open_late(dine_in_hours) if dine_in_hours else False,
            "open_late_drive_thru": is_open_late(drive_thru_hours) if drive_thru_hours else False,
            # New fields for frontend popup
            "phone_number": row[15],
            "ubereats_link": row[16],
            "doordash_link": row[17],
        })
    return jsonify(result)

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')
@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/static/images/logos/<path:company_name>')
def serve_company_logo(company_name):
    """
    Securely serve company logo images with long cache headers.
    Tries .webp first (smallest), then .png, then .jpg. Falls back to default if none found.
    """
    logo_dir = os.path.join(app.root_path, 'static', 'images', 'logos')
    raw_name = company_name.strip().lower().replace(" ", "-").replace("'", "").replace("&", "and")
    sanitized = secure_filename(raw_name)
    name, ext = os.path.splitext(sanitized)
    # Debug: Print Accept header and sanitized name
    accept_header = request.headers.get('Accept', '')
    accepts_webp = 'image/webp' in accept_header
    tried_files = []
    # Always try WebP first if browser supports it, regardless of what exists
    extensions = ['.webp', '.png', '.jpg'] if accepts_webp else ['.png', '.jpg']
    # Try each extension in order
    for ext_candidate in extensions:
        filename = f"{name}{ext_candidate}"
        filepath = os.path.join(logo_dir, filename)
        tried_files.append(filename)
        if os.path.exists(filepath):
            response = make_response(send_from_directory(logo_dir, filename))
            # Set appropriate content type
            if ext == '.webp':
                response.headers['Content-Type'] = 'image/webp'
            elif ext == '.png':
                response.headers['Content-Type'] = 'image/png'
            elif ext == '.jpg':
                response.headers['Content-Type'] = 'image/jpeg'
            
            # Long cache headers for performance
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Vary'] = 'Accept'  # Important for WebP content negotiation
            
            return response

    # Try default fallback (check WebP default first if supported)
    fallback_extensions = ['.webp', '.png', '.jpg'] if accepts_webp else ['.png', '.jpg']
    for ext in fallback_extensions:
        fallback = f'default{ext}'
        fallback_path = os.path.join(logo_dir, fallback)
        if os.path.exists(fallback_path):
            response = make_response(send_from_directory(logo_dir, fallback))
            # Set appropriate content type for fallback
            if ext == '.webp':
                response.headers['Content-Type'] = 'image/webp'
            elif ext == '.png':
                response.headers['Content-Type'] = 'image/png'
            elif ext == '.jpg':
                response.headers['Content-Type'] = 'image/jpeg'
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Vary'] = 'Accept'
            return response
    abort(404)

if __name__ == "__main__":
    app.run(debug=True, port=5000)