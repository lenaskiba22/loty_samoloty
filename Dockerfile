# Using the official Airflow 3 image
FROM apache/airflow:3.1.0

# Install the MSSQL provider and necessary drivers
# We use the 'airflow' user to ensure permissions are correct
USER airflow
RUN pip install --no-cache-dir \
    apache-airflow-providers-microsoft-mssql \
    pandas \
    sqlalchemy \
    duckdb  \
    timezonefinder \
    pyodbc \
    holidays