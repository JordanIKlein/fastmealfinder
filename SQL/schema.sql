CREATE TABLE companies (
    name TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    website TEXT,
    budget_friendly BOOLEAN DEFAULT FALSE,
    deals BOOLEAN DEFAULT FALSE
);
CREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    company_id TEXT REFERENCES companies(name),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE restaurant_locations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    company_id TEXT REFERENCES companies(name),
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    phone_number TEXT,
    -- Features
    has_drive_thru BOOLEAN DEFAULT FALSE,
    has_wifi BOOLEAN DEFAULT FALSE,
    has_online_ordering BOOLEAN DEFAULT FALSE,
    has_catering BOOLEAN DEFAULT FALSE,
    has_parking BOOLEAN DEFAULT FALSE,
    has_delivery BOOLEAN DEFAULT FALSE,
    has_mobile_ordering BOOLEAN DEFAULT FALSE,
    -- Hours
    dine_in_hours JSONB,
    drive_thru_hours JSONB 
);
