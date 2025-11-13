import psycopg2
from datetime import datetime

# Database connection parameters
DB_NAME = "fastmealfinder_qa"
DB_USER = "larry"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"
import psycopg2

companies = {
    "Burger King": "https://www.burgerking.com",
    "McDonald's": "https://www.mcdonalds.com",
    "Wendy's": "https://www.wendys.com",
    "Domino's": "https://www.dominos.com",
    "Chipotle": "https://www.chipotle.com",
    "Chick-fil-A": "https://www.chick-fil-a.com",
    "Taco Bell": "https://www.tacobell.com",
    "Subway": "https://www.subway.com",
    "Starbucks": "https://www.starbucks.com",
    "Dunkin": "https://www.dunkindonuts.com",
    "Panera Bread": "https://www.panerabread.com",
    "Pizza Hut": "https://www.pizzahut.com",
    "Sonic": "https://www.sonicdrivein.com",
    "Panda Express": "https://www.pandaexpress.com",
    "KFC": "https://www.kfc.com",
    "Popeyes": "https://www.popeyes.com",
    "Dairy Queen": "https://www.dairyqueen.com",
    "Jack in the Box": "https://www.jackinthebox.com",
    "Papa John's": "https://www.papajohns.com",
    "Whataburger": "https://www.whataburger.com",
    "Jersey Mike's Subs": "https://www.jerseymikes.com",
    "Five Guys": "https://www.fiveguys.com",
    "Crumbl Cookies": "https://www.crumblcookies.com",
    "Shake Shack": "https://www.shakeshack.com",
    "Cava": "https://www.cava.com"
}


try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    for name, website in companies.items():
        cur.execute("""
            INSERT INTO companies (name, website, budget_friendly, deals)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                website = EXCLUDED.website,
                budget_friendly = EXCLUDED.budget_friendly,
                deals = EXCLUDED.deals,
                updated_at = CURRENT_TIMESTAMP;
        """, (name, website, True, True))

    conn.commit()
    cur.close()
    conn.close()
    print("Company data inserted successfully.")

except Exception as e:
    print("An error occurred:", e)
