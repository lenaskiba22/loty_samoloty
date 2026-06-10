-- Stwórz bazę flight_dw jeśli nie istnieje
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'flight_dw')
BEGIN
    CREATE DATABASE flight_dw;
END
GO

USE flight_dw;
GO

-- Tabela logów
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ETL_Load_Log' AND xtype='U')
CREATE TABLE ETL_Load_Log (
    file_name      VARCHAR(100) PRIMARY KEY,
    loaded_at      DATETIME DEFAULT GETDATE(),
    records_loaded INT,
    status         VARCHAR(20)
);
GO

-- Wymiary
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Airline' AND xtype='U')
CREATE TABLE Dim_Airline (
    airline_code VARCHAR(2)   PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Airport' AND xtype='U')
CREATE TABLE Dim_Airport (
    airport_code VARCHAR(3)   PRIMARY KEY,
    airport_name VARCHAR(150),
    city         VARCHAR(100),
    state        VARCHAR(10),
    latitude     DECIMAL(9,6),
    longitude    DECIMAL(9,6),
    timezone     VARCHAR(50),
    type         VARCHAR(20)
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Date' AND xtype='U')
CREATE TABLE Dim_Date (
    flight_date   DATE        PRIMARY KEY,
    year          INT,
    quarter       INT,
    month         INT,
    day_of_week   VARCHAR(15),
    is_weekend    BIT,
    is_us_holiday BIT
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Weather' AND xtype='U')
CREATE TABLE Dim_Weather (
    category_id      INT         PRIMARY KEY,
    wmo_code_from    INT,
    wmo_code_to      INT,
    wmo_description  VARCHAR(100),
    weather_category VARCHAR(20),
    is_adverse       BIT
);
GO

-- Tabela faktów
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fact_Flights' AND xtype='U')
CREATE TABLE Fact_Flights (
    flight_id            INT         PRIMARY KEY,
    airline_code         VARCHAR(2)  REFERENCES Dim_Airline(airline_code),
    origin_airport_code  VARCHAR(3)  REFERENCES Dim_Airport(airport_code),
    dest_airport_code    VARCHAR(3)  REFERENCES Dim_Airport(airport_code),
    flight_date          DATE        REFERENCES Dim_Date(flight_date),
    weather_category_id  INT         REFERENCES Dim_Weather(category_id),
    arr_delay            FLOAT,
    dep_delay            FLOAT,
    carrier_delay        FLOAT,
    weather_delay        FLOAT,
    nas_delay            FLOAT,
    security_delay       FLOAT,
    late_aircraft_delay  FLOAT,
    taxi_out             FLOAT,
    taxi_in              FLOAT,
    elapsed_time         FLOAT,
    crs_elapsed_time     FLOAT,
    air_time             FLOAT,
    distance             FLOAT,
    dep_hour             INT,
    time_block           VARCHAR(20),
    cancelled            BIT,
    cancellation_code    VARCHAR(1),
    cancellation_reason  VARCHAR(25),
    diverted             BIT,
    is_delayed           BIT,
    temperature_c        DECIMAL(4,1),
    precipitation_mm     DECIMAL(5,2),
    windspeed_kmh        DECIMAL(5,2)
);
GO